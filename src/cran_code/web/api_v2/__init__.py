"""API v2 routers for Cran Code collaboration platform."""

from __future__ import annotations

from fastapi import APIRouter

from cran_code.web.api_v2 import auth, collab, fs, projects, teams, terminal, users

v2_router = APIRouter()
v2_router.include_router(auth.router)
v2_router.include_router(users.router)
v2_router.include_router(teams.router)
v2_router.include_router(projects.router)
v2_router.include_router(fs.router)
v2_router.include_router(collab.router)
v2_router.include_router(terminal.router)
