import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, Optional
import asyncio
import httpx


class OnvistaService:
    """
    Service for fetching financial instrument data from Onvista.
    Used specifically for derivatives and other instruments available on Onvista.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    async def get_instrument_data(self, isin: str) -> Optional[Dict]:
        """
        Get name, Geldkurs, and currency for any financial instrument.

        Args:
            isin: The ISIN (International Securities Identification Number) to look up

        Returns:
            Dict with name, price, and currency, or None if not found
        """
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
                response = await client.get(
                    f"https://www.onvista.de/suche/?searchValue={isin}",
                    follow_redirects=True,
                )

                if response.status_code != 200:
                    return None

                soup = BeautifulSoup(response.text, "html.parser")
                page_text = soup.get_text()

                if isin not in page_text:
                    return None

                # Extract name from title
                title = soup.find("title")
                name = None
                if title and "•" in title.text and "Aktueller Kurs" in title.text:
                    parts = title.text.split("•")
                    for part in parts:
                        if "Aktueller Kurs" in part:
                            name = part.replace("Aktueller Kurs", "").strip()[:80]
                            break

                # Extract Geldkurs (bid price)
                geld_match = re.search(
                    r"Geld[\s:]*(\d{1,4}[,\.]\d{2,4})", page_text, re.IGNORECASE
                )
                price = None
                if geld_match:
                    try:
                        price = float(geld_match.group(1).replace(",", "."))
                    except ValueError:
                        pass

                # Fallback to first EUR price
                if not price:
                    eur_match = re.search(r"(\d{1,4}[,\.]\d{2,4})\s*EUR", page_text)
                    if eur_match:
                        try:
                            price = float(eur_match.group(1).replace(",", "."))
                        except ValueError:
                            pass

                # Validate the extracted data
                if name and price and 0.001 <= price <= 100000:
                    return {
                        "name": name,
                        "price": price,
                        "currency": "EUR",  # Onvista primarily uses EUR
                    }

                return None

        except Exception as e:
            print(f"[OnvistaService] Error fetching data for ISIN {isin}: {e}")
            return None


# Global instance for reuse
onvista_service = OnvistaService()
