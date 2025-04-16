import uvicorn

if __name__ == "__main__":
    # for development
    uvicorn.run("app.main:app", port=8000, reload=True)
    
    # for production
    # uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 