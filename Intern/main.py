import os
import sys
import traceback

# Append current directory to path to allow direct imports of sibling modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from typing import List
from fastapi import FastAPI, HTTPException, Request, Depends, Response, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from calculator import CalculationRequest, CalculationResponse, run_calculation
import db

app = FastAPI(title="Vessel Laycan & Demurrage Calculator")

# Initialize SQLite database on startup
db.init_db()

# Request Models
class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: str = "user"

class UserResponse(BaseModel):
    username: str
    role: str

# Dependency for authentication
def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
        
    user_info = db.validate_session(token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid"
        )
        
    return user_info

# Dependency for admin-only routes
def get_current_admin(user_info = Depends(get_current_user)):
    if user_info["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user_info


# --- AUTH API ---
@app.post("/api/auth/login")
def login(req: LoginRequest, response: Response):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, role FROM users WHERE username = ?", (req.username.strip().lower(),))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not db.verify_password(req.password, row['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
        
    token = db.create_session(req.username)
    # Set HTTP-only cookie for sessions
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=86400, # 24 hours
        samesite="lax"
    )
    return {"token": token, "username": req.username, "role": row['role']}

@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            
    if token:
        db.delete_session(token)
        
    response.delete_cookie("session_token")
    return {"success": True}

@app.get("/api/auth/me", response_model=UserResponse)
def get_me(user_info = Depends(get_current_user)):
    return user_info


# --- USER MANAGEMENT API (Admin Only) ---
@app.get("/api/users", response_model=List[UserResponse])
def get_users(admin_info = Depends(get_current_admin)):
    return db.list_users()

@app.post("/api/users")
def add_user(req: UserCreateRequest, admin_info = Depends(get_current_admin)):
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
        
    if req.role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'user'")
        
    success = db.create_user(req.username, req.password, req.role)
    if not success:
        raise HTTPException(status_code=400, detail="Username already exists")
    return {"success": True}

@app.delete("/api/users/{username}")
def remove_user(username: str, admin_info = Depends(get_current_admin)):
    if username.strip().lower() == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete default admin account")
        
    success = db.delete_user(username)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True}


# --- CALCULATIONS & HISTORY API ---
@app.post("/api/calculate", response_model=CalculationResponse)
def calculate(req: CalculationRequest, user_info = Depends(get_current_user)):
    try:
        res = run_calculation(req)
        # Convert Pydantic request & response to dicts for SQLite storage
        req_dict = req.dict()
        res_dict = res.dict()
        
        # Serialize datetime date/time fields to string for JSON serialization inside DB
        req_dict['laycan_start'] = req_dict['laycan_start'].isoformat()
        req_dict['laycan_end'] = req_dict['laycan_end'].isoformat()
        req_dict['arrival_time'] = req_dict['arrival_time'].isoformat()
        req_dict['nor_tendered'] = req_dict['nor_tendered'].isoformat()
        req_dict['nor_accepted'] = req_dict['nor_accepted'].isoformat()
        req_dict['loading_arm_disconnected'] = req_dict['loading_arm_disconnected'].isoformat()
        
        res_dict['laycan_start_time'] = res_dict['laycan_start_time'].isoformat()
        
        # Save to SQLite
        db.save_calculation(user_info["username"], req_dict, res_dict)
        return res
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/calculations")
def get_history(user_info = Depends(get_current_user)):
    return db.get_calculations(user_info["username"], user_info["role"])

@app.delete("/api/calculations/{calc_id}")
def delete_history_item(calc_id: int, user_info = Depends(get_current_user)):
    success = db.delete_calculation(calc_id, user_info["username"], user_info["role"])
    if not success:
        raise HTTPException(status_code=404, detail="Calculation not found or not owned by you")
    return {"success": True}


# --- STATIC FILES ---
# Get base path of this file to find static folder
base_path = os.path.dirname(os.path.abspath(__file__))
static_path = os.path.join(base_path, "static")

# Ensure static directory exists
os.makedirs(static_path, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Serve index.html at root
@app.get("/")
def read_index():
    index_file = os.path.join(static_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Server is running, but static/index.html was not found. Please create it."}
