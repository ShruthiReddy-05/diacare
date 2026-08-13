import random
import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db
from models.user import User, ParticipantRecoveryEvent, AppSession
from schemas.user import UserCreate, UserResponse, UserRecovery, LanguageUpdate, AppSessionCreate, AppSessionResponse

router = APIRouter(prefix="/api/users", tags=["Users"])

async def generate_display_user_id(db: AsyncSession, first_name: str, last_name: str) -> str:
    fn_clean = re.sub(r'[^a-zA-Z]', '', first_name).lower()
    ln_clean = re.sub(r'[^a-zA-Z]', '', last_name).lower()

    fn_part = fn_clean[:4] if fn_clean else "user"
    ln_part = ln_clean[:4] if ln_clean else "df"
    len_part = f"{len(fn_clean)}{len(ln_clean)}"

    base_id = f"{fn_part}{ln_part}{len_part}"

    stmt = select(User).where(User.display_user_id == base_id)
    result = await db.execute(stmt)
    if result.scalar() is None:
        return base_id

    for _ in range(100):
        suffix = f"{random.randint(0, 99):02d}"
        display_id = f"{base_id}{suffix}"
        stmt = select(User).where(User.display_user_id == display_id)
        result = await db.execute(stmt)
        if result.scalar() is None:
            return display_id

    import uuid
    return f"{base_id}{str(uuid.uuid4())[:4]}"

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Generate unique display user ID
    display_id = await generate_display_user_id(db, user_in.first_name, user_in.last_name)
    
    db_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        preferred_language=user_in.preferred_language,
        display_user_id=display_id,
        role="participant"
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post("/recover", response_model=UserResponse)
async def recover_user(recovery_in: UserRecovery, db: AsyncSession = Depends(get_db)):
    # Search for user by display_user_id
    stmt = select(User).where(
        User.display_user_id == recovery_in.display_user_id.strip().lower()
    )
    result = await db.execute(stmt)
    db_user = result.scalar()
    
    # Verify first/last name matches (case-insensitive)
    matched = False
    if db_user:
        fn_match = db_user.first_name.strip().lower() == recovery_in.first_name.strip().lower()
        ln_match = db_user.last_name.strip().lower() == recovery_in.last_name.strip().lower()
        if fn_match and ln_match:
            matched = True
            
    # Log recovery attempt
    event = ParticipantRecoveryEvent(
        user_id=db_user.id if db_user else "unknown",
        display_user_id_entered=recovery_in.display_user_id,
        first_name_entered=recovery_in.first_name,
        last_name_entered=recovery_in.last_name,
        result="matched" if matched else "not_matched"
    )
    db.add(event)
    await db.commit()
    
    if not matched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile recovery failed. Display ID or names do not match any registered user."
        )
        
    return db_user

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    db_user = result.scalar()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    return db_user

@router.patch("/{user_id}/language", response_model=UserResponse)
async def update_language(user_id: str, lang_in: LanguageUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    db_user = result.scalar()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    db_user.preferred_language = lang_in.preferred_language
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post("/{user_id}/sessions", response_model=AppSessionResponse)
async def create_app_session(user_id: str, session_in: AppSessionCreate, db: AsyncSession = Depends(get_db)):
    # Verify user exists
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    if not result.scalar():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
        
    db_session = AppSession(
        user_id=user_id,
        entry_source=session_in.entry_source,
        language=session_in.language
    )
    db.add(db_session)
    await db.commit()
    await db.refresh(db_session)
    return db_session
