# flight_search_api.py
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from typing import Optional
from flight_search_automation import search_and_scrape

app = FastAPI()

@app.get("/flight-search")
def flight_search(origin: str = Query(...), destination: str = Query(...), journey_date: str = Query(...)):
    """
    Example:
    GET /flight-search?origin=Bangalore&destination=Delhi&journey_date=2025-10-25
    """
    try:
        # Run the Playwright scraper synchronously; headless True for server
        results = search_and_scrape(origin, destination, journey_date, headless=True)
        return JSONResponse(content=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# If run directly, start uvicorn (not required if using other ASGI server)
if __name__ == "__main__":
    uvicorn.run("flight_search_api:app", host="0.0.0.0", port=8000, reload=False)
