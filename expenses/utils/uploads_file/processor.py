import csv
from io import StringIO


class UploadProcessor:
    def __init__(self, content):
        self.content = content

    def generate_json(self):
        """
         Process the CSV content and generate a JSON-like structure.
         The structure must:
         {
            "dimension": {
                "rows": number of rows,
                "cols": number of columns,
            },
            "parameters": {},
            "data": [
                [row1_col1, row1_col2, ...],
                [row2_col1, row2_col2, ...],
                ...
            ]}
        }
        """
        csv_file = StringIO(self.content)
        reader = csv.reader(csv_file)

        body = {
            "dimension": {
                "rows": 0,
                "cols": 0,
            },
            "parameters": {},
            "data": [],
        }
        key = 0
        num_cols = 0
        # Fill the dictionary with data, using one of the fields (e.g., name) as the key
        for row in reader:
            l_row = list(row)
            l_row.insert(0, key)
            body["data"].append(l_row)
            num_cols = max(num_cols, len(l_row))
            key += 1

        num_rows = key
        body["dimension"]["rows"] = num_rows
        body["dimension"]["cols"] = num_cols
        return body
