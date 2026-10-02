"""
reader.py

Reads fixed-size binary .stat files and displays the records.

Jake Fowlie - 10185046
"""

import struct
import sys
from collections import defaultdict


MAGIC = b"STAT"
VERSION = 1

RECORD_FORMAT = "<IIIBHHHHHHhHI"
HEADER_FORMAT = "<4sBBII"
CHECKSUM_FORMAT = "<I"

HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
RECORD_SIZE = struct.calcsize(RECORD_FORMAT)
CHECKSUM_SIZE = struct.calcsize(CHECKSUM_FORMAT)


def read_exactly(file_object, number_of_bytes):
    """
    Read exactly number_of_bytes from the file.
    """

    data = file_object.read(number_of_bytes)

    if len(data) != number_of_bytes:
        raise EOFError(
            f"Expected {number_of_bytes} bytes, "
            f"got {len(data)} bytes"
        )

    return data


def read_header(file_object):
    """
    Read and validate the header.

    Returns:
        raw header bytes, decoded header dictionary
    """

    header_bytes = read_exactly(
        file_object,
        HEADER_SIZE,
    )

    (
        magic,
        version,
        flags,
        record_size,
        record_count,
    ) = struct.unpack(
        HEADER_FORMAT,
        header_bytes,
    )

    if magic != MAGIC:
        raise ValueError(
            f"Invalid magic number: {magic}"
        )

    if version != VERSION:
        raise ValueError(
            f"Unsupported version: {version}"
        )

    if record_size != RECORD_SIZE:
        raise ValueError(
            f"Unexpected record size: {record_size}"
        )

    return (
        header_bytes,
        {
            "magic": magic,
            "version": version,
            "flags": flags,
            "record_size": record_size,
            "record_count": record_count,
        },
    )


def code_to_position(code):
    """
    Convert a position code to a human-readable position.
    """

    positions = {
        1: "C",
        2: "LW",
        3: "RW",
        4: "D",
        5: "G",
    }

    if code not in positions:
        raise ValueError(
            f"Invalid position code: {code}"
        )

    return positions[code]


def unpack_record(record_bytes):
    """
    Unpack one fixed-size binary record.
    """

    if len(record_bytes) != RECORD_SIZE:
        raise ValueError(
            "Record data size does not match "
            f"RECORD_SIZE: {len(record_bytes)} bytes"
        )

    values = struct.unpack(
        RECORD_FORMAT,
        record_bytes,
    )

    (
        game_id,
        team_id,
        player_id,
        position_code,
        goals,
        assists,
        points,
        shots,
        hits,
        blocked_shots,
        plus_minus,
        penalty_minutes,
        time_on_ice_seconds,
    ) = values

    if points != goals + assists:
        raise ValueError(
            f"Points ({points}) does not equal "
            f"goals ({goals}) + assists ({assists})"
        )

    return {
        "game_id": game_id,
        "team_id": team_id,
        "player_id": player_id,
        "position_code": position_code,
        "goals": goals,
        "assists": assists,
        "points": points,
        "shots": shots,
        "hits": hits,
        "blocked_shots": blocked_shots,
        "plus_minus": plus_minus,
        "penalty_minutes": penalty_minutes,
        "time_on_ice_seconds": time_on_ice_seconds,
    }


def calculate_checksum(data):
    """
    Calculate the same checksum used by writer.py.
    """

    return sum(data) % (2 ** 32)


def read_stat_file(file_path):
    """
    Read a .stat file and return decoded records.
    """

    records = []

    with open(file_path, "rb") as source:
        header_bytes, header = read_header(source)

        record_data = bytearray()

        for _ in range(header["record_count"]):
            record_bytes = read_exactly(
                source,
                RECORD_SIZE,
            )

            record_data.extend(record_bytes)

            # Decode only the current record.
            record = unpack_record(record_bytes)
            records.append(record)

        checksum_bytes = read_exactly(
            source,
            CHECKSUM_SIZE,
        )

        stored_checksum = struct.unpack(
            CHECKSUM_FORMAT,
            checksum_bytes,
        )[0]

        body = header_bytes + bytes(record_data)
        calculated_checksum = calculate_checksum(body)

        if stored_checksum != calculated_checksum:
            raise ValueError(
                "Checksum mismatch: "
                f"stored {stored_checksum}, "
                f"calculated {calculated_checksum}"
            )

        extra_data = source.read()

        if extra_data:
            raise ValueError(
                "Extra data found after checksum"
            )

    return records


def build_index(records):
    """
    Build indexes for player and game lookups.

    player_index[player_id][game_id] = record
    game_index[game_id][player_id] = record
    """

    player_index = defaultdict(dict)
    game_index = defaultdict(dict)

    for record in records:
        game_id = record["game_id"]
        player_id = record["player_id"]

        if game_id in player_index[player_id]:
            raise ValueError(
                "Duplicate record for "
                f"game_id {game_id} and "
                f"player_id {player_id}"
            )

        player_index[player_id][game_id] = record
        game_index[game_id][player_id] = record

    return player_index, game_index


def find_player_record(
    player_index,
    game_id,
    player_id,
):
    """
    Find one player's record in one game.
    """

    if player_id not in player_index:
        raise ValueError(
            f"No records found for player_id {player_id}"
        )

    if game_id not in player_index[player_id]:
        raise ValueError(
            f"No record found for player_id {player_id} "
            f"in game_id {game_id}"
        )

    return player_index[player_id][game_id]


def find_player_records_by_game(
    player_index,
    player_id,
):
    """
    Find all game records for one player.
    """

    if player_id not in player_index:
        return []

    return list(
        player_index[player_id].values()
    )


def find_game_records(game_index, game_id):
    """
    Find all player records for one game.
    """

    if game_id not in game_index:
        return []

    return list(
        game_index[game_id].values()
    )


def format_time_on_ice(seconds):
    """
    Convert seconds to MM:SS.
    """

    minutes = seconds // 60
    remaining_seconds = seconds % 60

    return f"{minutes:02}:{remaining_seconds:02}"


def format_record(record):
    """
    Convert a record into readable output.
    """

    position = code_to_position(
        record["position_code"]
    )

    time_on_ice = format_time_on_ice(
        record["time_on_ice_seconds"]
    )

    return {
        "game_id": record["game_id"],
        "team_id": record["team_id"],
        "player_id": record["player_id"],
        "position": position,
        "goals": record["goals"],
        "assists": record["assists"],
        "points": record["points"],
        "shots": record["shots"],
        "hits": record["hits"],
        "blocked_shots": record["blocked_shots"],
        "plus_minus": record["plus_minus"],
        "penalty_minutes": record["penalty_minutes"],
        "time_on_ice": time_on_ice,
    }


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python reader.py "
            "<path_to_stat_file>"
        )
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        records = read_stat_file(file_path)
    except (
        OSError,
        ValueError,
        EOFError,
        struct.error,
    ) as error:
        print(f"Error: {error}")
        sys.exit(1)

    print(f"Read {len(records)} records")

    for record in records:
        print()
        print(format_record(record))


if __name__ == "__main__":
    main()