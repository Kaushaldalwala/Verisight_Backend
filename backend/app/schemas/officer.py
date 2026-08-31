from pydantic import BaseModel, Field, model_validator

try:
    from pydantic import EmailStr
except Exception:
    EmailStr = str  # Fallback to plain string if email-validator package is absent


class OfficerSignup(BaseModel):
    first_name:    str = Field(..., min_length=1, max_length=100)
    last_name:     str = Field(..., min_length=1, max_length=100)
    officer_id:    str = Field(..., min_length=2, max_length=50)
    officer_email: str = Field(..., min_length=3, max_length=150)
    organization:  str = Field(..., min_length=2, max_length=200)
    designation:   str = Field(..., min_length=2, max_length=200)
    password:      str = Field(..., min_length=8)


class OfficerLogin(BaseModel):
    """Sign in with officer_id or officer_email plus password."""
    officer_id:    str | None = Field(None, min_length=2, max_length=50)
    officer_email: str | None = None
    password:      str = Field(..., min_length=8)

    @model_validator(mode="after")
    def require_id_or_email(self):
        if not self.officer_id and not self.officer_email:
            raise ValueError("Provide either officer_id or officer_email.")
        return self


class OfficerProfile(BaseModel):
    id:            str
    first_name:    str
    last_name:     str
    officer_id:    str
    officer_email: str
    organization:  str
    designation:   str
    created_at:    str | None = None
    updated_at:    str | None = None


class TokenRefresh(BaseModel):
    refresh_token: str
