import re
import socket
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from src.services.ai_service import ai_service
from src.errors import InvalidInputError, SDKConnectionError
from src.logger import logger

class AgentService:
    """
    AI Agent Service for extracting web page content and generating
    structured summaries using Muse Spark.
    """
    def __init__(self, ai_svc=None):
        self.ai_svc = ai_svc or ai_service

    def validate_and_parse_url(self, url):
        """
        Validates URL format and checks against SSRF (no local/loopback/private IPs).
        """
        if not url:
            raise InvalidInputError("URL cannot be empty")
        
        # Ensure it has a protocol scheme
        if not re.match(r'^https?://', url, re.IGNORECASE):
            url = "http://" + url
            
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                raise InvalidInputError("Invalid URL domain or address structure")
                
            # Perform basic hostname check (SSRF protection)
            hostname = parsed.hostname
            if not hostname:
                raise InvalidInputError("Invalid URL hostname")

            # Try resolving hostname to IP
            try:
                ip = socket.gethostbyname(hostname)
            except socket.gaierror:
                # Could be a domain that doesn't resolve; we let the fetch handle it or throw
                ip = None
                
            if ip:
                if self._is_private_ip(ip):
                    logger.warning(f"Prevented SSRF attempt to private/local IP: {ip} for host {hostname}")
                    raise InvalidInputError("Access to internal, private, or local network resources is restricted.")
            
            return url
        except InvalidInputError:
            raise
        except Exception as e:
            logger.error(f"URL parsing exception: {e}")
            raise InvalidInputError(f"URL validation failed: {str(e)}")

    def _is_private_ip(self, ip_str):
        """Helper to determine if an IP address is loopback, link-local, or private."""
        # Check standard loopback, private ranges
        if ip_str.startswith("127.") or ip_str == "::1" or ip_str == "0.0.0.0":
            return True
        
        # Private Class A: 10.0.0.0 - 10.255.255.255
        if ip_str.startswith("10."):
            return True
            
        # Private Class B: 172.16.0.0 - 172.31.255.255
        if ip_str.startswith("172."):
            parts = ip_str.split('.')
            if len(parts) >= 2:
                try:
                    second_octet = int(parts[1])
                    if 16 <= second_octet <= 31:
                        return True
                except ValueError:
                    pass
                    
        # Private Class C: 192.168.0.0 - 192.168.255.255
        if ip_str.startswith("192.168."):
            return True
            
        # Link-local: 169.254.0.0 - 169.254.255.255
        if ip_str.startswith("169.254."):
            return True
            
        return False

    def fetch_and_clean_webpage(self, url):
        """
        Downloads a webpage and strips out navigation, advertisements,
        footers, scripts, and styling to retrieve only meaningful content.
        """
        headers = {
            "User-Agent": "MuseSparkExplorerAgent/1.0 (Python HTTPX; Cloud-Ready Demo)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        
        try:
            logger.info(f"Agent fetching webpage: {url}")
            # Follow redirects up to 5 times, 10s timeout
            with httpx.Client(follow_redirects=True, timeout=10.0) as client:
                response = client.get(url, headers=headers)
                
            if response.status_code >= 400:
                logger.error(f"Failed to fetch webpage. Status code: {response.status_code}")
                raise SDKConnectionError(f"Target server returned HTTP error status {response.status_code}")
                
            html_content = response.text
        except httpx.TimeoutException:
            logger.error("Webpage request timed out.")
            raise SDKConnectionError("Webpage request timed out after 10 seconds.")
        except httpx.RequestError as e:
            logger.error(f"Webpage fetch request error: {e}")
            raise SDKConnectionError(f"Target page is unreachable or address is invalid: {str(e)}")

        # Clean HTML content with BeautifulSoup
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Remove scripts, styles, forms, noscripts, IFrames, ads, navigation, header, footer
            for element in soup(["script", "style", "noscript", "iframe", "form", "nav", "header", "footer"]):
                element.decompose()

            # Remove typical advertising class/id containers
            ad_patterns = re.compile(r'ad|advertisement|banner|sponsor|social-share|footer-links', re.IGNORECASE)
            for div in soup.find_all(class_=ad_patterns):
                div.decompose()
            for div in soup.find_all(id=ad_patterns):
                div.decompose()

            # Extract main article title
            title = ""
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
            elif soup.h1:
                title = soup.h1.get_text().strip()

            # Extract text elements
            text_blocks = []
            
            # Target articles or main body div if available, otherwise just use paragraphs
            main_content = soup.find('main') or soup.find('article') or soup.find('div', id='content') or soup.find('div', class_='content')
            
            if main_content:
                paragraphs = main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li'])
            else:
                paragraphs = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li'])

            for p in paragraphs:
                txt = p.get_text().strip()
                if len(txt) > 20: # Skip very short snippets
                    text_blocks.append(txt)

            clean_text = "\n\n".join(text_blocks)
            # Remove duplicate whitespaces
            clean_text = re.sub(r'\n\s*\n+', '\n\n', clean_text)
            
            word_count = len(clean_text.split())
            # Estimate reading time (average 200 words per minute)
            reading_time_min = max(1, round(word_count / 200))
            
            if word_count < 10:
                raise InvalidInputError("Webpage has insufficient extractable text content to summarize.")
                
            return {
                "title": title or "Untitled Webpage",
                "clean_text": clean_text[:8000],  # Limit to 8000 characters for safety
                "word_count": word_count,
                "reading_time": reading_time_min
            }
        except InvalidInputError:
            raise
        except Exception as e:
            logger.error(f"HTML cleaning pipelines failed: {e}")
            raise MuseSparkError(f"Error parsing page structures: {str(e)}")

    def summarize_webpage(self, url):
        """
        Main pipeline:
        1. Validate URL.
        2. Fetch & clean page.
        3. Invoke Muse Spark to create summary outputs.
        """
        validated_url = self.validate_and_parse_url(url)
        parsed_data = self.fetch_and_clean_webpage(validated_url)
        
        prompt = (
            f"You are Muse Spark, a helpful AI Agent. Summarize the following webpage content.\n\n"
            f"Webpage Title: {parsed_data['title']}\n"
            f"URL: {validated_url}\n\n"
            f"Webpage Content:\n"
            f"{parsed_data['clean_text']}\n\n"
            f"Provide a structured response using the following format:\n"
            f"### SUMMARY\n"
            f"[Provide a concise 3-4 sentence paragraph summary of the page]\n\n"
            f"### KEY POINTS\n"
            f"- [Key point 1]\n"
            f"- [Key point 2]\n"
            f"- [Key point 3]\n\n"
            f"### ACTION ITEMS\n"
            f"- [Action item or take-away 1]\n"
            f"- [Action item or take-away 2]\n"
        )
        
        # Call SDK completions non-streaming
        messages = [{"role": "user", "content": prompt}]
        
        try:
            logger.info("Sending extracted webpage contents to Muse Spark for summarization.")
            # Set temperature low (0.3) for factual summarization
            # Set max_tokens to 1000
            response = self.ai_svc.client.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=1000,
                stream=False
            )
            
            # Record telemetry stats
            self.ai_svc._record_activity("Webpage Agent Summarization", response.latency, success=True)
            
            # Parse responses
            summary_content = response.content
            
            # Extract sections using simple regex
            summary_match = re.search(r'### SUMMARY\n(.*?)(?=\n\n###|$)', summary_content, re.DOTALL | re.IGNORECASE)
            key_points_match = re.search(r'### KEY POINTS\n(.*?)(?=\n\n###|$)', summary_content, re.DOTALL | re.IGNORECASE)
            action_items_match = re.search(r'### ACTION ITEMS\n(.*?)(?=\n\n###|$)', summary_content, re.DOTALL | re.IGNORECASE)
            
            summary = summary_match.group(1).strip() if summary_match else "Summary section could not be parsed."
            key_points = key_points_match.group(1).strip() if key_points_match else "- Key points could not be parsed."
            action_items = action_items_match.group(1).strip() if action_items_match else "- Action items could not be parsed."
            
            # If standard regex parsing fails to isolate sections, provide raw summary fallback
            if "could not be parsed" in summary and "could not be parsed" in key_points:
                summary = summary_content
                key_points = "- Content retrieved as a single block."
                action_items = "- Review raw summary contents."

            return {
                "title": parsed_data["title"],
                "url": validated_url,
                "word_count": parsed_data["word_count"],
                "reading_time": parsed_data["reading_time"],
                "summary": summary,
                "key_points": key_points,
                "action_items": action_items,
                "latency_sec": response.latency
            }
        except Exception as e:
            logger.error(f"Webpage summarization API request failed: {e}")
            raise MuseSparkError(f"Muse Spark failed to summarize the page content: {str(e)}")

# Create global agent service
agent_service = AgentService()
