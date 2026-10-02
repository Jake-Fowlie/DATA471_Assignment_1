"""
writer.py

Converts NHL-style CSV player-game statistics into a fixed-size
binary .stat file.

Each record represents one player's performance in one game.

Jake Fowlie - 10185046
"""

import csv
import struct
import sys
from pathlib import Path


MAGIC = b"STAT"
VERSION = 1

# Field order:
# game_id
# team_id
# player_id
# position_code
# goals
# assists
# points
# shots
# hits
# blocked_shots
# plus_minus
# penalty_minutes
# time_on_ice_seconds

# <  = little-endian
# I  = unsigned 32-bit integer
# B  = unsigned 8-bit integer
# H  = unsigned 16-bit integer
# h  = signed 16-bit integer
RECORD_FORMAT = "<IIIBHHHHHHhHI"

HEADER_FORMAT = "<4sBBII"
CHECKSUM_FORMAT = "<I"

HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
RECORD_SIZE = struct.calcsize(RECORD_FORMAT)
CHECKSUM_SIZE = struct.calcsize(CHECKSUM_FORMAT)

REQUIRED_COLUMNS = (
    "game_id",
    "team_id",
    "player_id",
    "position_code",
    "goals",
    "assists",
    "points",
    "shots",
    "hits",
    "blocked_shots",
    "plus_minus",
    "penalty_minutes",
    "time_on_ice_seconds",
)


def validate_record(record, seen_keys):
    """
    Validate and convert one CSV row.

    The unique identity of a record is:
        (game_id, player_id)

    Jersey numbers are not used as identifiers.
    """

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in record
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(missing_columns)}"
        )

    

    integer_fields = (
        "game_id",
        "team_id",
        "player_id",
        "position_code",
        "goals",
        "assists",
        "points",
        "shots",
        "hits",
        "blocked_shots",
        "plus_minus",
        "penalty_minutes",
        "time_on_ice_seconds",
    )

    cleaned_record = {}

    for field in integer_fields:
        value = record[field]

        if value is None or value.strip() == "":
            raise ValueError(f"Missing value for {field}")

        try:
            cleaned_record[field] = int(value)
        except ValueError as error:
            raise ValueError(
                f"Invalid integer value for {field}: {value}"
            ) from error

    for field in ("game_id", "team_id", "player_id"):
        if cleaned_record[field] <= 0:
            raise ValueError(
                f"{field} must be a positive integer"
            )

    if not 1 <= cleaned_record["position_code"] <= 5:
        raise ValueError(
            "position_code must be between 1 and 5"
        )

    nonnegative_fields = (
        "goals",
        "assists",
        "points",
        "shots",
        "hits",
        "blocked_shots",
        "penalty_minutes",
        "time_on_ice_seconds",
    )

    for field in nonnegative_fields:
        if cleaned_record[field] < 0:
            raise ValueError(
                f"{field} must be non-negative"
            )

    if cleaned_record["points"] != (
        cleaned_record["goals"] + cleaned_record["assists"]
    ):
        raise ValueError(
            "points must equal goals plus assists"
        )

    key = (
        cleaned_record["game_id"],
        cleaned_record["player_id"],
    )

    if key in seen_keys:
        raise ValueError(
            "duplicate player-game record for "
            f"game {key[0]}, player {key[1]}"
        )

    seen_keys.add(key)

    return cleaned_record


def pack_record(record):
    """
    Convert one validated record into fixed-size binary data.
    """

    values = (
        record["game_id"],
        record["team_id"],
        record["player_id"],
        record["position_code"],
        record["goals"],
        record["assists"],
        record["points"],
        record["shots"],
        record["hits"],
        record["blocked_shots"],
        record["plus_minus"],
        record["penalty_minutes"],
        record["time_on_ice_seconds"],
    )

    encoded_record = struct.pack(RECORD_FORMAT, *values)

    if len(encoded_record) != RECORD_SIZE:
        raise ValueError(
            "Encoded record size does not match RECORD_SIZE"
        )

    return encoded_record


def create_header(record_count):
    """
    Create the binary file header.
    """

    flags = 1  # Bit 0 means a checksum is present.

    return struct.pack(
        HEADER_FORMAT,
        MAGIC,
        VERSION,
        flags,
        RECORD_SIZE,
        record_count,
    )


def calculate_checksum(data):
    """
    Calculate a simple 32-bit byte-sum checksum.
    """

    return sum(data) % (2 ** 32)


def write_stat_file(input_csv, output_stat):
    """
    Read CSV records and create a binary .stat file.
    """

    records = []
    seen_keys = set()

    with open(
        input_csv,
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as source:
        csv_reader = csv.DictReader(source)
        csv_reader = csv.DictReader(source)
        

        if csv_reader.fieldnames is None:
            raise ValueError("CSV file does not contain a header")

        csv_reader.fieldnames = [field.replace("\ufeff", "").strip() for field in csv_reader.fieldnames
        ]

        

        missing_columns = [
            column for column in REQUIRED_COLUMNS
            if column not in csv_reader.fieldnames
        ]

        if missing_columns:
            raise ValueError(
                "Missing required columns: "
                + ", ".join(missing_columns)
            )

        for row_number, row in enumerate(csv_reader, start=2):
            try:
                validated_record = validate_record(
                    row,
                    seen_keys,
                )
            except ValueError as error:
                raise ValueError(
                    f"Invalid CSV row {row_number}: {error}"
                ) from error

            records.append(validated_record)
        

    encoded_records = []

    for record in records:
        encoded_record = pack_record(record)
        encoded_records.append(encoded_record)

    header = create_header(len(encoded_records))
    record_data = b"".join(encoded_records)
    body = header + record_data

    checksum = calculate_checksum(body)
    packed_checksum = struct.pack(
        CHECKSUM_FORMAT,
        checksum,
    )

    output_path = Path(output_stat)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(output_path, "wb") as destination:
        destination.write(body)
        destination.write(packed_checksum)

    total_size = len(body) + len(packed_checksum)

    print(f"Wrote {len(records)} records to {output_path}")
    print(f"Record size: {RECORD_SIZE} bytes")
    print(f"File size: {total_size} bytes")

    

def main():
    """
    Usage:

        python writer.py input.csv output.stat
    """

    if len(sys.argv) != 3:
        print(
            "Usage: python writer.py "
            "input.csv output.stat"
        )
        sys.exit(1)

    input_csv = sys.argv[1]
    output_stat = sys.argv[2]

    try:
        write_stat_file(input_csv, output_stat)
    except (OSError, ValueError, struct.error) as error:
        print(f"Error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()