# Repository Usage Examples

This document provides comprehensive examples of using the repository pattern for database operations.

## Table of Contents

1. [User Management](#user-management)
2. [Sprite Operations](#sprite-operations)
3. [Music Track Operations](#music-track-operations)
4. [Sound Effect Operations](#sound-effect-operations)
5. [Script Operations](#script-operations)
6. [Audit Logging](#audit-logging)
7. [Transaction Management](#transaction-management)
8. [Advanced Queries](#advanced-queries)

---

## User Management

### Creating a User

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.repositories import UserRepository
from backend.models import UserRole

@app.post("/api/users/register")
async def register_user(
    username: str,
    password: str,
    email: str,
    db: AsyncSession = Depends(get_db)
):
    user_repo = UserRepository(db)

    # Check if user exists
    existing_user = await user_repo.get_by_username(username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Create user
    user = await user_repo.create(
        username=username,
        password=password,  # Automatically hashed
        email=email,
        role=UserRole.USER,
        full_name="John Doe"
    )

    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role
    }
```

### User Authentication

```python
@app.post("/api/auth/login")
async def login(
    username: str,
    password: str,
    db: AsyncSession = Depends(get_db)
):
    user_repo = UserRepository(db)

    # Authenticate user
    user = await user_repo.authenticate(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate session token
    # ... token generation logic ...

    return {
        "access_token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role
        }
    }
```

### Getting User Information

```python
@app.get("/api/users/{user_id}")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at.isoformat(),
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
    }
```

### Updating User

```python
@app.patch("/api/users/{user_id}")
async def update_user(
    user_id: str,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    user_repo = UserRepository(db)

    update_data = {}
    if email:
        update_data["email"] = email
    if full_name:
        update_data["full_name"] = full_name

    user = await user_repo.update(user_id, **update_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "User updated successfully", "user_id": user.id}
```

### Listing Users (Admin)

```python
@app.get("/api/admin/users")
async def list_users(
    limit: int = 50,
    offset: int = 0,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    user_repo = UserRepository(db)

    users = await user_repo.list_all(
        limit=limit,
        offset=offset,
        active_only=active_only
    )

    total = await user_repo.count(active_only=active_only)

    return {
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat()
            }
            for u in users
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }
```

---

## Sprite Operations

### Creating a Sprite

```python
from backend.repositories import SpriteRepository

@app.post("/api/sprites")
async def create_sprite(
    description: str,
    file_path: str,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sprite_repo = SpriteRepository(db)

    sprite = await sprite_repo.create(
        user_id=current_user.id,
        description=description,
        file_path=file_path,
        width=32,
        height=32,
        format="PNG",
        category=category or "general",
        tags=tags or [],
        metadata={"source": "user_upload"}
    )

    return {
        "sprite_id": sprite.sprite_id,
        "description": sprite.description,
        "file_path": sprite.file_path
    }
```

### Getting User's Sprites

```python
@app.get("/api/sprites")
async def list_my_sprites(
    limit: int = 50,
    offset: int = 0,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sprite_repo = SpriteRepository(db)

    sprites = await sprite_repo.list_by_user(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        category=category
    )

    total = await sprite_repo.count_by_user(current_user.id)

    return {
        "sprites": [
            {
                "sprite_id": s.sprite_id,
                "description": s.description,
                "file_path": s.file_path,
                "category": s.category,
                "tags": s.tags,
                "created_at": s.created_at.isoformat()
            }
            for s in sprites
        ],
        "total": total
    }
```

### Updating Sprite Metadata

```python
@app.patch("/api/sprites/{sprite_id}")
async def update_sprite(
    sprite_id: str,
    description: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sprite_repo = SpriteRepository(db)

    # Verify ownership
    sprite = await sprite_repo.get_by_id(sprite_id)
    if not sprite or sprite.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Sprite not found")

    # Update
    update_data = {}
    if description:
        update_data["description"] = description
    if category:
        update_data["category"] = category
    if tags is not None:
        update_data["tags"] = tags

    updated_sprite = await sprite_repo.update(sprite_id, **update_data)

    return {"message": "Sprite updated", "sprite_id": updated_sprite.sprite_id}
```

---

## Music Track Operations

### Creating a Music Track

```python
from backend.repositories import MusicRepository

@app.post("/api/music")
async def create_music_track(
    description: str,
    file_path: str,
    duration_seconds: float,
    category: str = "background",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    music_repo = MusicRepository(db)

    track = await music_repo.create(
        user_id=current_user.id,
        description=description,
        file_path=file_path,
        duration_seconds=duration_seconds,
        format="MOD",
        category=category,
        tags=["game", "retro"],
        metadata={"bpm": 120, "key": "C major"}
    )

    return {
        "track_id": track.track_id,
        "description": track.description
    }
```

---

## Sound Effect Operations

### Creating a Sound Effect

```python
from backend.repositories import SFXRepository

@app.post("/api/sfx")
async def create_sound_effect(
    description: str,
    file_path: str,
    effect_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sfx_repo = SFXRepository(db)

    sfx = await sfx_repo.create(
        user_id=current_user.id,
        description=description,
        file_path=file_path,
        effect_type=effect_type,
        format="WAV",
        sample_rate=44100,
        category="ui",
        tags=["button", "click"]
    )

    return {
        "sfx_id": sfx.sfx_id,
        "description": sfx.description
    }
```

---

## Script Operations

### Creating a Script

```python
from backend.repositories import ScriptRepository

@app.post("/api/scripts")
async def create_script(
    name: str,
    events: dict,
    script_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    script_repo = ScriptRepository(db)

    script = await script_repo.create(
        user_id=current_user.id,
        name=name,
        events=events,
        script_type=script_type,
        description="Auto-generated script",
        category="gameplay",
        complexity_score=len(events.get("events", []))
    )

    return {
        "script_id": script.script_id,
        "name": script.name
    }
```

---

## Audit Logging

### Logging User Actions

```python
from backend.repositories import AuditRepository

async def log_action(
    action: str,
    user_id: str,
    resource_type: str,
    resource_id: str,
    request: Request,
    success: bool,
    db: AsyncSession
):
    audit_repo = AuditRepository(db)

    await audit_repo.create(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        endpoint=str(request.url),
        method=request.method,
        status_code=200 if success else 500,
        success=success,
        details={"timestamp": datetime.utcnow().isoformat()}
    )
```

### Viewing Audit Logs (Admin)

```python
@app.get("/api/admin/audit-logs")
async def get_audit_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    audit_repo = AuditRepository(db)

    if user_id:
        logs = await audit_repo.list_by_user(user_id, limit=limit, offset=offset)
    elif action:
        logs = await audit_repo.list_by_action(action, limit=limit, offset=offset)
    else:
        raise HTTPException(status_code=400, detail="Provide user_id or action")

    return {
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "timestamp": log.timestamp.isoformat(),
                "success": log.success
            }
            for log in logs
        ]
    }
```

---

## Transaction Management

### Multiple Operations in Single Transaction

```python
@app.post("/api/projects")
async def create_project_with_assets(
    project_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create project with multiple assets in a single transaction"""
    try:
        sprite_repo = SpriteRepository(db)
        music_repo = MusicRepository(db)
        audit_repo = AuditRepository(db)

        # Create sprites
        sprites = []
        for sprite_data in project_data.get("sprites", []):
            sprite = await sprite_repo.create(
                user_id=current_user.id,
                **sprite_data
            )
            sprites.append(sprite)

        # Create music tracks
        tracks = []
        for music_data in project_data.get("music", []):
            track = await music_repo.create(
                user_id=current_user.id,
                **music_data
            )
            tracks.append(track)

        # Log action
        await audit_repo.create(
            user_id=current_user.id,
            action="project_created",
            resource_type="project",
            resource_id=project_data.get("id"),
            success=True
        )

        # Transaction commits automatically on success
        return {
            "message": "Project created successfully",
            "sprites_count": len(sprites),
            "tracks_count": len(tracks)
        }

    except Exception as e:
        # Transaction rolls back automatically on exception
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Advanced Queries

### Search with Multiple Filters

```python
@app.get("/api/sprites/search")
async def search_sprites(
    query: Optional[str] = None,
    category: Optional[str] = None,
    min_date: Optional[datetime] = None,
    max_date: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sprite_repo = SpriteRepository(db)

    # Use search method
    sprites = await sprite_repo.search(
        user_id=current_user.id,
        category=category,
        limit=limit,
        offset=offset
    )

    # Additional filtering can be done in repository
    # For text search, you'd add a custom method to repository

    return {
        "sprites": [
            {
                "sprite_id": s.sprite_id,
                "description": s.description,
                "category": s.category,
                "created_at": s.created_at.isoformat()
            }
            for s in sprites
        ]
    }
```

### Cleanup Old Records

```python
@app.post("/api/admin/cleanup-audit-logs")
async def cleanup_audit_logs(
    days: int = 90,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Clean up audit logs older than specified days"""
    audit_repo = AuditRepository(db)

    deleted_count = await audit_repo.cleanup_old_logs(days=days)

    return {
        "message": f"Cleaned up {deleted_count} old audit log entries",
        "deleted_count": deleted_count,
        "retention_days": days
    }
```

---

## Best Practices

1. **Always use repositories** - Don't write raw SQL queries
2. **Use transactions** - Multiple operations should be in one transaction
3. **Validate input** - Check data before passing to repositories
4. **Handle errors** - Catch and properly handle database exceptions
5. **Log important actions** - Use audit logging for sensitive operations
6. **Check ownership** - Verify user owns resource before modifying
7. **Use pagination** - Always limit and offset large result sets
8. **Index optimization** - Use indexed fields in queries when possible
9. **Avoid N+1 queries** - Use joins or eager loading when needed
10. **Clean up old data** - Regularly clean up audit logs and temp data
