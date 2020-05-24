from pathlib import Path
import pandas as pd
import datetime
import json
import os


def get_number_of_files(dir) -> int:
    """
    utility function to determine number of files in a directory
    :param dir: path to directory
    :return: number of files in <dir>
    """
    count = 0
    for _, _, files in os.walk(dir):
        count += len([filename for filename in files if filename[0] != "."])
    return count


def get_project_root() -> Path:
    """utility function to return the project root folder

    Returns:

    """
    return Path(__file__).parent.parent


def convert_to_flare(file_path,out_path=None):
    """utility function that reads in .csv file and converts it to a .json formatted file to be used in the visualization

    """
    df = __read_file(file_path)

    df = df.groupby("file_path").aggregate(**{
        "LOC":       pd.NamedAgg(column="line_number", aggfunc="count"),
        "#authors":  pd.NamedAgg(column="author", aggfunc="nunique"),
        "old_lines": pd.NamedAgg(column="older_six_months", aggfunc=lambda old_lines: sum(old_lines)),
        "new_lines": pd.NamedAgg(column="older_six_months", aggfunc=lambda old_lines: sum(~old_lines)),
        "authors":   pd.NamedAgg(column="author", aggfunc=lambda x: list(x.unique()))
    })

    df["fraction_old_lines"] = round((df["old_lines"] / df["LOC"]), 2)
    df.reset_index(inplace=True)
    __pack_flare(df,out_path)


def __read_file(file_path):
    df = pd.read_csv(file_path)
    df["author-date"] = pd.to_datetime(df["author-time"], unit="s")
    six_months_ago = datetime.date.today() - pd.offsets.DateOffset(months=3)
    df["older_six_months"] = df["author-date"] < six_months_ago
    df.drop(labels=["author-mail", "author-tz", "author-time", "committer", "committer-mail", "committer-time",
                    "committer-tz", "summary", "changed_line"],
            axis=1, inplace=True)
    return df


def __pack_flare(df,out_path):
    json_data = {"name": ".", "children": []}
    for row in df.iterrows():
        series = row[1]  # Row-Inhalt extrahieren
        path, filename = os.path.split(series['file_path'])  # Spalte in Pfad und Dateinamen aufteilen"

        last_children = None
        children = json_data['children']

        for path_part in path.split("\\"):
            entry = None

            for child in children:
                if "name" in child and child["name"] == path_part:
                    entry = child
            if not entry:
                entry = {}
                children.append(entry)
            entry['name'] = path_part
            if not 'children' in entry:
                entry['children'] = []
            children = entry['children']
            last_children = children
        leaf_dict = {}
        leaf_dict['name'] = filename
        leaf_dict['size'] = series["LOC"]
        leaf_dict['authors'] = ",".join(series["authors"])
        leaf_dict['author_count'] = series["#authors"]
        leaf_dict["fraction_of_lines_older_6_months"] = "{:6.2f}".format(series["fraction_old_lines"]).strip()
        last_children.append(leaf_dict)

    file_path = os.path.join(get_project_root(), "files", "flare.json")
    with open(file_path, mode='w', encoding='utf-8') as json_file:
        json_file.write(json.dumps(json_data, indent=3))