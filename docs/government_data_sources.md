# Government Data Sources & Official Integration Analysis

**Project:** VeriSight Document Screening Platform  
**Purpose:** Investigation of legitimate government data sources, APIs, and fallback strategies.

---

## 1. Overview & Priority Policy

VeriSight enforces a strict data source priority policy:

```
Official Government API (Authorized Credentials)
       ↓
Official Published Dataset / Specification
       ↓
Synthetic Reference Dataset (Development / Prototype Fallback)
```

---

## 2. Document-Specific Government Source Analysis

### Passport (ICAO Doc 9303 / PKD)
- **Official Source:** ICAO Public Key Directory (PKD) & National Passport Issuing Authority APIs (e.g. US Department of State, Passport Seva India).
- **Access Protocol:** Requires official diplomatic / border control authorization and signed PKI certificates.
- **Integration Status:** `GovernmentProvider` implements OAuth2/API Key client interface. Unconfigured environments seamlessly fall back to synthetic database.

### Visa
- **Official Source:** National Immigration & Customs Enforcement Databases (e.g. US ESTA/EVUS, Schengen VIS, India e-Visa Portal).
- **Access Protocol:** Restrictive government-to-government web services (REST/SOAP over mTLS).
- **Integration Status:** Architecture prepared in `GovernmentProvider`. Credentials read from `GOV_API_URL` and `GOV_API_KEY`.

### Aadhaar (India Unique Identification Authority of India - UIDAI)
- **Official Source:** UIDAI Aadhaar Verification API / QR Code Verification / Digilocker API.
- **Access Protocol:** Requires ASA/KUA licensing and registered device biometric/OTP authentication.
- **Local Validation:** Verhoeff mathematical checksum validation implemented locally without external network call.

### Driving License
- **Official Source:** Parivahan Sewa (mParivahan API / NDL Portal) for India; DMV State APIs for US.
- **Access Protocol:** Restricted API token with government enterprise agreement.
- **Fallback:** Synthetic database containing 5,000+ realistic Indian & international license records.

---

## 3. Security & Ethics Directives

1. **No Unauthorized Access:** Never attempt to scrape, bypass CAPTCHA, or breach restricted government infrastructure.
2. **No Leaked Data:** System strictly prohibits indexing or using leaked or compromised databases.
3. **Synthetic Labeling:** All non-official demonstration data is explicitly labeled as `SYNTHETIC / DEMONSTRATION DATA`.
