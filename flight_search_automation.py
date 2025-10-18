# flight_search_automation.py
# Playwright (sync) script that opens budgetticket.in, searches flights, extracts visible results,
# saves to flight_results.json and prints total number extracted.
#
# Usage (example from command line):
# python flight_search_automation.py "Bangalore" "Delhi" "2025-10-25"

import sys
import json
from datetime import datetime, timezone
from time import sleep
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

def search_and_scrape(origin: str, destination: str, journey_date: str, headless=True):
    """
    Returns a list of dictionaries with keys:
      airline, flight_number, departure, arrival, price, origin, destination, searchdatetime
    """
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        # 1) Open the site
        page.goto("https://www.budgetticket.in", timeout=60000)

        # NOTE: website structure may change; below attempts to interact with common flight-search fields.
        # 2) Click / open flight search form if needed
        try:
            # If there's a flights tab/button, click it (commonly labeled Flights)
            flight_tab = page.query_selector("a[href*='flights'], button:has-text('Flights'), text=Flights")
            if flight_tab:
                flight_tab.click()
        except Exception:
            pass


        # 3) Fill origin and destination - try multiple selector options
        # --- fill origin & destination ---
        # def fill_input_with_suggestion(page, selector, value):
        #     el = page.query_selector(selector)
        #     el.click()
        #     el.fill(value)
        #     page.wait_for_timeout(1000)
        #     page.keyboard.press("ArrowDown")
        #     page.keyboard.press("Enter")
        #     page.wait_for_timeout(500)

        # fill_input_with_suggestion(page, "input[placeholder='Select Origin City']", origin)
        # fill_input_with_suggestion(page, "input[placeholder='Select Destination City']", destination)
        def fill_input_with_suggestion(page, selector, value, field_type):
            el = page.query_selector(selector)
            if not el:
                print(f"❌ Could not find {field_type} field with selector: {selector}")
                return False
    
            el.click()
    # Clear the field first
            el.fill("")
            page.wait_for_timeout(500)
    
    # Type the value character by character to trigger suggestions
            el.fill(value)
            page.wait_for_timeout(2000)  # Wait longer for suggestions to appear
    
    # Press ArrowDown to select first suggestion and press Enter
            page.keyboard.press("ArrowDown")
            page.wait_for_timeout(500)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1000)
    
    # Verify the filled value
            filled_value = el.input_value()
            print(f"✅ Filled {field_type}: {filled_value}")
    
            return True

# Usage with field type identification
        fill_input_with_suggestion(page, "input[placeholder='Select Origin City']", origin, "origin")
        page.wait_for_timeout(2000)  # Important: wait between filling fields
        fill_input_with_suggestion(page, "input[placeholder='Select Destination City']", destination, "destination")



        # origin_selectors = ["input[placeholder='Select Origin City']"]
        # destination_selectors = ["input[placeholder='Select Destination City']"]



        # filled_origin = fill_input(origin_selectors, origin)
        # filled_dest = fill_input(destination_selectors, destination)

        # 4) Fill journey date - try common date picker selectors
        date_selectors = ["label.datepicker.search-date"]

        date_filled = False
        for sel in date_selectors:
            try:
                el = page.query_selector(sel)
                if el:
                    el.click()
                    sleep(1)
                    break
            except Exception:
                continue

        # If direct fill not reliable, attempt to type and press Enter
        if not date_filled:
            page.keyboard.type(journey_date)

        # 5) Click search button (try common selectors)
        search_button_selectors = ["input[type='submit'][value='Search']"]



        clicked_search = False
        for sel in search_button_selectors:
            try:
                btn = page.query_selector(sel)
                if btn:
                    btn.click()
                    clicked_search = True
                    break
            except Exception:
                continue
        if not clicked_search:
            # fallback: press Enter
            page.keyboard.press("Enter")

        # 6) Wait until search results load - wait for a likely results container
        try:
            # wait for typical results container; adjust timeout if slow
            page.wait_for_selector(".flight-list, .search-results, .result, [data-search-result]", timeout=30000)
        except PWTimeoutError:
            # continue anyway; sometimes results are lazy-loaded
            pass

        # Give additional time for dynamic data to fully load
        sleep(3)

        # 7) Extract each visible flight - try to find repeated item containers
        # We'll look for common patterns and then extract fields using relative selectors.
        possible_item_selectors = [".search-list-item"]



        items = []
        for sel in possible_item_selectors:
            found = page.query_selector_all(sel)
            if found and len(found) > 0:
                items = found
                break

        # If none found, attempt a generic approach: collect elements that look like flight cards by structure
        if not items:
            # Heuristic: find containers that have time-like texts and price inside
            all_divs = page.query_selector_all("div")
            for d in all_divs:
                text = d.inner_text().strip()
                if text.count(":") >= 1 and ("₹" in text or "Rs." in text or "INR" in text or "Price" in text):
                    items.append(d)
            # deduplicate
            items = list(dict.fromkeys(items))

        # For each found item try extracting fields
        for item in items:
            try:
                txt = item.inner_text()
                # Airline name (try common subselectors)
                airline = None
                for s in [".airline", ".airline-name", ".carrier", ".flight-airline"]:
                    sub = item.query_selector(s)
                    if sub:
                        airline = sub.inner_text().strip()
                        break
                if not airline:
                    # heuristic: first line of the item text that contains letters and not times/prices
                    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
                    for ln in lines:
                        if any(c.isalpha() for c in ln) and not (":" in ln and ln.replace(":", "").strip().isdigit()):
                            airline = ln
                            break

                # Flight number
                flight_number = None
                for s in [".flight-number", ".flight-no", ".number"]:
                    sub = item.query_selector(s)
                    if sub:
                        flight_number = sub.inner_text().strip()
                        break
                if not flight_number:
                    # regex-like heuristic from text
                    parts = txt.split()
                    for p in parts:
                        if any(p.startswith(pref) for pref in ("6E", "AI", "UK", "SG", "IX", "G8", "JA", "IX", "AI-","6E-")) or "-" in p and any(ch.isdigit() for ch in p):
                            flight_number = p.strip()
                            break

                # Departure and arrival times
                departure = None
                arrival = None
                # common subselectors
                dep_sub = item.query_selector(".departure, .dep-time, .time-depart")
                arr_sub = item.query_selector(".arrival, .arr-time, .time-arrive")
                if dep_sub:
                    departure = dep_sub.inner_text().strip()
                if arr_sub:
                    arrival = arr_sub.inner_text().strip()

                # fallback: find time patterns in text (HH:MM)
                if not departure or not arrival:
                    import re
                    times = re.findall(r"\b([0-2]?\d:[0-5]\d)\b", txt)
                    if times:
                        if len(times) >= 2:
                            departure, arrival = times[0], times[1]
                        elif len(times) == 1 and not departure:
                            departure = times[0]

                # Price
                price = None
                for s in [".price", ".fare", ".ticket-price", ".amount"]:
                    sub = item.query_selector(s)
                    if sub:
                        price = sub.inner_text().strip()
                        break
                if not price:
                    # heuristic search in text
                    import re
                    price_match = re.search(r"(₹\s?[0-9,]+|Rs\.?\s?[0-9,]+|INR\s?[0-9,]+)", txt)
                    if price_match:
                        price = price_match.group(0).strip()

                # Build dictionary only if at least price and one time is present to avoid junk
                if price or (departure and arrival):
                    entry = {
                        "airline": airline if airline else "",
                        "flight_number": flight_number if flight_number else "",
                        "departure": departure if departure else "",
                        "arrival": arrival if arrival else "",
                        "price": price if price else "",
                        "origin": origin,
                        "destination": destination,
                        "searchdatetime": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                    }
                    results.append(entry)
            except Exception:
                # skip items that cause errors
                continue

        # Close browser
        context.close()
        browser.close()

    # Deduplicate results by a combination of airline+flight_number+departure
    seen = set()
    unique_results = []
    for r in results:
        key = (r.get("airline",""), r.get("flight_number",""), r.get("departure",""))
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    # Save to flight_results.json
    with open("flight_results.json", "w", encoding="utf-8") as f:
        json.dump(unique_results, f, ensure_ascii=False, indent=2)

    # Print total extracted
    print(f"Total Flights Extracted: {len(unique_results)}")

    return unique_results

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python flight_search_automation.py <origin> <destination> <journey_date (YYYY-MM-DD)>")
        sys.exit(1)
    origin = sys.argv[1]
    destination = sys.argv[2]
    journey_date = sys.argv[3]
    search_and_scrape(origin, destination, journey_date, headless=False)



