"""
ADAM Platform: Main Application Entry Point

This is the main entry point for the ADAM Psychological Intelligence Platform.
"""

from fastapi import FastAPI

app = FastAPI(
    title="ADAM Platform",
    description="Atomic Decision & Audience Modeling - Psychological Intelligence System",
    version="4.0.0"
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "4.0.0", "specs_complete": 30, "specs_remaining": 1}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
