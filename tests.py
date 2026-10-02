"""
tests.py

Tests the NHL-style binary .stat file.

Jake Fowlie - 10185046
"""

from pathlib import Path

import writer
import reader

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data/cleaned_data"
OUTPUT_DIR = BASE_DIR / "output"

DATASET_1 = DATA_DIR / "nhl_game_1.csv"
DATASET_2 = DATA_DIR / "nhl_game_2.csv"

STAT_FILE_1 = OUTPUT_DIR / "game_1.stat"
STAT_FILE_2 = OUTPUT_DIR / "game_2.stat"

CORRUPTED_STAT_FILE = OUTPUT_DIR / "corrupted.stat"


# 1. Writing CSV data to a .stat file and reading it back should yield the same data.
def test_basic_round_trip():
    writer.write_stat_file(DATASET_1, STAT_FILE_1)

    assert STAT_FILE_1.exists(), ("STAT file was not created: {0}").format(STAT_FILE_1)

    records = reader.read_stat_file(STAT_FILE_1)

    assert len(records) > 0, "No records were read from the STAT file"

    print(f"Read {len(records)} records from {STAT_FILE_1}")

    return records



# 2. The player look-up functionality should return the correct records for a given player_id.
def test_player_look_up(records):

    player_index, game_index = reader.build_index(records)

    player_id = records[0]["player_id"]

    player_records = reader.find_player_records_by_game(player_index, player_id)

    assert len(player_records) > 0, (
        "No records found for player_id: {0}").format(player_id)

    for record in player_records:
        assert record["player_id"] == player_id, (
            "Record player_id does not match expected player_id: {0}").format(player_id)

    print("PASS: player look-up functionality")

# 3. The player-game look-up functionality should return the correct record for a given player_id and game_id.
def test_player_game_lookup(records):
    player_index, game_index = reader.build_index(records)

    expected_record = records[0]

    result = reader.find_player_record(
        player_index,
        expected_record["game_id"],
        expected_record["player_id"],
    )

    assert result is not None, (
        "No record found for player_id: {0}, game_id: {1}").format(expected_record["player_id"], expected_record["game_id"])

    assert result["player_id"] == expected_record["player_id"], (
        "Record player_id does not match expected player_id: {0}").format(expected_record)

    assert result["game_id"] == expected_record["game_id"], (
        "Record game_id does not match expected game_id: {0}").format(expected_record)

    print("PASS: player-game look-up functionality")

# 4. The game look-up functionality should return the correct records for a given game_id.
def test_game_lookup(records):
    player_index, game_index = reader.build_index(records)

    game_id = records[0]["game_id"]

    game_records = reader.find_game_records(game_index, game_id)

    assert len(game_records) > 0, (
        "No records found for game_id: {0}").format(game_id)

    for record in game_records:
        assert record["game_id"] == game_id, (
            "Record game_id does not match expected game_id: {0}").format(game_id)

    print("PASS: game look-up functionality")

# 5. Testing with a second dataset
def test_second_dataset():
    writer.write_stat_file(DATASET_2, STAT_FILE_2)

    assert STAT_FILE_2.exists(), ("STAT file was not created: {0}").format(STAT_FILE_2)

    records = reader.read_stat_file(STAT_FILE_2)

    assert len(records) > 0, "No records were read from the STAT file"

    print(f"Read {len(records)} records from {STAT_FILE_2}")

    return records

# 6. Testing with a corrupted .stat file
def test_corrupted_stat_file():

    writer.write_stat_file(DATASET_1, CORRUPTED_STAT_FILE)


    with open(CORRUPTED_STAT_FILE, "r+b") as f:
        f.truncate(100) 

    try:
        reader.read_stat_file(CORRUPTED_STAT_FILE)
        assert False, "Expected an exception when reading a corrupted .stat file"
    except Exception as e:
        print(f"PASS: Caught expected exception for corrupted .stat file: {e}")

def main():
    records = test_basic_round_trip()
    test_player_look_up(records)
    test_player_game_lookup(records)
    test_game_lookup(records)
    test_second_dataset()
    test_corrupted_stat_file()

    print("All tests passed successfully.")

if __name__ == "__main__":
    main()