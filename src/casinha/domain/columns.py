"""Column-name constants shared across services and pages."""

TIMESTAMP = "Timestamp_1"
COLUMN_NO = "Column_No"

FIRST_NAME = "First name"
LAST_NAME = "Last name"
DATE_OF_BIRTH = "Date of birth"
NATIONALITY = "Nationality"
CITY_OF_BIRTH = "City of birth"
CITY_OF_RESIDENCE = "City of residence"
COUNTRY_OF_RESIDENCE = "Country of residence"
PASSPORT_NUMBER = "Passport (or ID) number"
COUNTRY_OF_ISSUE = "Country of issue"
CHECKIN_DATE = "Check-in date"
CHECKOUT_DATE = "Check-out date"

SEF_DISPLAY_COLS = [
    FIRST_NAME,
    LAST_NAME,
    CHECKIN_DATE,
    CHECKOUT_DATE,
    DATE_OF_BIRTH,
    NATIONALITY,
    CITY_OF_BIRTH,
    CITY_OF_RESIDENCE,
    COUNTRY_OF_RESIDENCE,
    PASSPORT_NUMBER,
    COUNTRY_OF_ISSUE,
]

INVOICE_DISPLAY_COLS = [
    FIRST_NAME,
    LAST_NAME,
    CHECKIN_DATE,
    CHECKOUT_DATE,
    PASSPORT_NUMBER,
    COUNTRY_OF_RESIDENCE,
]
