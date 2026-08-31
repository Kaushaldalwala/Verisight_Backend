"""
seed.py

Synthetic Data Generator for VeriSight Validation Engine.

Populates SQLite database with large-scale synthetic test records (35,000+ total).
Distribution is configurable: ~70% ACTIVE, 10% EXPIRED, 5% REVOKED, 5% BLACKLISTED, 5% MALFORMED, 5% INCONSISTENT.

CLEAR DISCLAIMER:
SYNTHETIC / DEMONSTRATION DATA
NOT FOR REAL-WORLD IDENTITY VERIFICATION.
"""

import argparse
import random
import uuid
from datetime import datetime, timedelta
import logging

from app.module2_validation.database.connection import get_db_connection, init_db
from app.module2_validation.database.repository import DocumentRepository

logger = logging.getLogger(__name__)

# Sample names for generation
FIRST_NAMES = [
    "ARJUN", "PRIYA", "RAHUL", "ANANYA", "VIKRAM", "SNEHA", "AMIT", "POOJA",
    "ROHAN", "KAVYA", "ADITYA", "NEHA", "SANJAY", "DIVYA", "KARAN", "MEERA",
    "JOHN", "EMMA", "MICHAEL", "SOPHIA", "DAVID", "OLIVIA", "JAMES", "EMILY",
]

LAST_NAMES = [
    "MEHTA", "SHARMA", "PATEL", "GUPTA", "SINGH", "VERMA", "KUMAR", "JOSHI",
    "REDDY", "NAIR", "RAO", "DESHMUKH", "SMITH", "JOHNSON", "BROWN", "WILLIAMS",
]

NATIONALITIES = ["IND", "USA", "GBR", "CAN", "AUS", "DEU", "FRA", "SGP"]

STATUS_DISTRIBUTION = [
    ("ACTIVE", 0.70),
    ("EXPIRED", 0.10),
    ("REVOKED", 0.05),
    ("BLACKLISTED", 0.05),
    ("SUSPENDED", 0.05),
    ("LOST", 0.05),
]


def random_status() -> str:
    r = random.random()
    cumulative = 0.0
    for status, prob in STATUS_DISTRIBUTION:
        cumulative += prob
        if r <= cumulative:
            return status
    return "ACTIVE"


def random_date(start_year: int = 1970, end_year: int = 2005) -> str:
    year = random.randint(start_year, end_year)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{year:04d}-{month:02d}-{day:02d}"


def seed_passports(conn, count: int) -> None:
    logger.info("Generating %d synthetic passport records...", count)
    data = []
    for i in range(1, count + 1):
        num = f"P{i:07d}"
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        fullname = f"{fname} {lname}"
        nat = random.choice(NATIONALITIES)
        dob = random_date(1965, 2003)
        issue_year = random.randint(2015, 2023)
        issue = f"{issue_year:04d}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        status = random_status()
        if status == "EXPIRED":
            expiry_year = random.randint(2018, 2023)
        else:
            expiry_year = random.randint(2027, 2035)
        expiry = f"{expiry_year:04d}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        gender = random.choice(["M", "F"])

        data.append((
            str(uuid.uuid4()), num, fullname, lname, nat, dob, issue, expiry, gender, status
        ))

    conn.executemany("""
        INSERT OR REPLACE INTO passports
        (id, passport_number, name, surname, nationality, date_of_birth, date_of_issue, date_of_expiry, gender, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()


def seed_visas(conn, count: int) -> None:
    logger.info("Generating %d synthetic visa records...", count)
    data = []
    for i in range(1, count + 1):
        num = f"V{i:08d}"
        pass_num = f"P{random.randint(1, 10000):07d}"
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        fullname = f"{fname} {lname}"
        nat = random.choice(NATIONALITIES)
        vtype = random.choice(["TOURIST", "BUSINESS", "STUDENT", "WORK"])
        dob = random_date(1965, 2003)
        status = random_status()
        issue = "2023-01-15"
        expiry = "2024-01-14" if status == "EXPIRED" else "2030-01-14"
        gender = random.choice(["M", "F"])

        data.append((
            str(uuid.uuid4()), num, pass_num, fullname, nat, vtype, dob, issue, expiry, gender, status
        ))

    conn.executemany("""
        INSERT OR REPLACE INTO visas
        (id, visa_number, passport_number, name, nationality, visa_type, date_of_birth, date_of_issue, date_of_expiry, gender, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()


def seed_aadhaars(conn, count: int) -> None:
    logger.info("Generating %d synthetic Aadhaar records...", count)
    data = []
    for i in range(1, count + 1):
        num = f"{i:012d}"
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        fullname = f"{fname} {lname}"
        dob = random_date(1965, 2005)
        gender = random.choice(["M", "F"])
        status = random_status()

        data.append((
            str(uuid.uuid4()), num, fullname, dob, gender, status
        ))

    conn.executemany("""
        INSERT OR REPLACE INTO aadhaars
        (id, aadhaar_number, name, date_of_birth, gender, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()


def seed_driving_licenses(conn, count: int) -> None:
    logger.info("Generating %d synthetic driving license records...", count)
    data = []
    for i in range(1, count + 1):
        num = f"DL{i:010d}"
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        fullname = f"{fname} {lname}"
        dob = random_date(1970, 2002)
        issue = "2015-05-10"
        status = random_status()
        expiry = "2020-05-09" if status == "EXPIRED" else "2035-05-09"
        bg = random.choice(["A+", "B+", "O+", "AB+"])
        rel = f"S/O {random.choice(FIRST_NAMES)} {lname}"

        data.append((
            str(uuid.uuid4()), num, fullname, dob, issue, expiry, bg, rel, status
        ))

    conn.executemany("""
        INSERT OR REPLACE INTO driving_licenses
        (id, license_number, name, date_of_birth, date_of_issue, date_of_expiry, blood_group, relation, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()


def seed_national_ids(conn, count: int) -> None:
    logger.info("Generating %d synthetic national ID records...", count)
    data = []
    for i in range(1, count + 1):
        num = f"NID{i:08d}"
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        fullname = f"{fname} {lname}"
        nat = random.choice(NATIONALITIES)
        dob = random_date(1970, 2002)
        status = random_status()
        expiry = "2022-01-01" if status == "EXPIRED" else "2032-01-01"
        gender = random.choice(["M", "F"])

        data.append((
            str(uuid.uuid4()), num, fullname, nat, dob, expiry, gender, status
        ))

    conn.executemany("""
        INSERT OR REPLACE INTO national_ids
        (id, id_number, name, nationality, date_of_birth, date_of_expiry, gender, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()


def seed_permits(conn, count: int) -> None:
    logger.info("Generating %d synthetic permit records...", count)
    data = []
    for i in range(1, count + 1):
        num = f"PER{i:08d}"
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        fullname = f"{fname} {lname}"
        ptype = random.choice(["WORK", "RESIDENCE", "ENTRY"])
        pass_num = f"P{random.randint(1, 10000):07d}"
        issue = "2023-01-01"
        status = random_status()
        expiry = "2023-12-31" if status == "EXPIRED" else "2028-12-31"

        data.append((
            str(uuid.uuid4()), num, fullname, ptype, pass_num, issue, expiry, status
        ))

    conn.executemany("""
        INSERT OR REPLACE INTO permits
        (id, permit_number, name, permit_type, passport_number, date_of_issue, date_of_expiry, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()


def seed_all(db_path: str | None = None, passports=10000, visas=10000, aadhaars=5000, licenses=5000, ids=5000, permits=5000, seed_val=42):
    random.seed(seed_val)
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        seed_passports(conn, passports)
        seed_visas(conn, visas)
        seed_aadhaars(conn, aadhaars)
        seed_driving_licenses(conn, licenses)
        seed_national_ids(conn, ids)
        seed_permits(conn, permits)
        logger.info("Synthetic database seeding complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed synthetic validation database for VeriSight")
    parser.add_argument("--passports", type=int, default=10000)
    parser.add_argument("--visas", type=int, default=10000)
    parser.add_argument("--aadhaars", type=int, default=5000)
    parser.add_argument("--licenses", type=int, default=5000)
    parser.add_argument("--national-ids", type=int, default=5000)
    parser.add_argument("--permits", type=int, default=5000)
    parser.add_argument("--count-only", action="store_true")
    args = parser.parse_args()

    repo = DocumentRepository()
    if args.count_only:
        for dtype in ["passport", "visa", "aadhaar", "driving_license", "national_id", "permit"]:
            print(f"{dtype:<20}: {repo.count_records(dtype):,} records")
    else:
        seed_all(
            passports=args.passports,
            visas=args.visas,
            aadhaars=args.aadhaars,
            licenses=args.licenses,
            ids=args.national_ids,
            permits=args.permits,
        )
