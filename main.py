from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import SessionLocal, init_db, User, Item, PhysicalCount
import pandas as pd
import PyPDF2
import io
import os

app = FastAPI()

init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_html():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/login")
def login(data: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.get("username"), User.password == data.get("password")).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"role": user.role, "username": user.username}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    items_added = 0
    
    try:
        if file.filename.endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(contents))
            for _, row in df.iterrows():
                sku = str(row.get('SKU', ''))
                if sku and not db.query(Item).filter(Item.sku == sku).first():
                    new_item = Item(sku=sku, description=str(row.get('Description', '')), book_qty=float(row.get('BookQty', 0)))
                    db.add(new_item)
                    items_added += 1
            db.commit()

        elif file.filename.endswith('.pdf'):
            reader = PyPDF2.PdfReader(io.BytesIO(contents))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            new_item = Item(sku=f"PDF-{file.filename[:5]}", description="Extracted from PDF", book_qty=0)
            db.add(new_item)
            db.commit()
            items_added += 1
            
        else:
            raise HTTPException(status_code=400, detail="Invalid file type. Use .xlsx or .pdf")
            
        return {"message": f"Successfully processed. Added {items_added} items."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/api/items")
def get_items(db: Session = Depends(get_db)):
    return db.query(Item).all()

@app.post("/api/count")
def submit_count(data: dict, db: Session = Depends(get_db)):
    new_count = PhysicalCount(item_id=data['item_id'], auditor_name=data['auditor'], qty=float(data['qty']))
    db.add(new_count)
    db.commit()
    return {"message": "Count submitted successfully!"}

@app.get("/api/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    items = db.query(Item).all()
    dashboard_data = []
    for item in items:
        total_physical = db.query(func.sum(PhysicalCount.qty)).filter(PhysicalCount.item_id == item.id).scalar() or 0.0
        variance = item.book_qty - total_physical
        dashboard_data.append({
            "sku": item.sku,
            "description": item.description,
            "book_qty": item.book_qty,
            "physical_qty": total_physical,
            "variance": variance
        })
    return dashboard_data

@app.get("/api/export")
def export_report(db: Session = Depends(get_db)):
    data = get_dashboard(db)
    df = pd.DataFrame(data)
    filepath = "static/Audit_Report.xlsx"
    df.to_excel(filepath, index=False)
    return FileResponse(filepath, filename="Audit_Report.xlsx")

@app.post("/api/reset")
def reset_data(db: Session = Depends(get_db)):
    try:
        db.query(PhysicalCount).delete()
        db.query(Item).delete()
        db.commit()
        return {"message": "All inventory and count data has been erased."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error resetting data: {str(e)}")
