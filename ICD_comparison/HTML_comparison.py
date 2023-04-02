import pandas as pd
import requests
from bs4 import BeautifulSoup
import numpy as np
import argparse
import webbrowser

result_file = """
<style>
/* Split the screen in half */
.split {
  height: 100%;
  width: 50%;
  position: fixed;
  z-index: 1;
  top: 0;
  overflow-x: hidden;
  padding-top: 20px;
}

/* Control the left side */
.left {
  left: 0;
<!--  background-color: #111;-->
}

/* Control the right side */
.right {
  right: 0;
<!--  background-color: red;-->
}

/* If you want the content centered horizontally and vertically */
.centered {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

/* Style the image inside the centered container, if needed */
.centered img {
  width: 150px;
  border-radius: 50%;
}

table, th, td {
    border: 1px solid black;
    border-collapse: collapse;
    background-color: #FFF;
}

th {
    background-color: #8900FD;
}

.EnumTable {
    width: 30%;
}

.DetectorInfoTable {
    width: 50%;
}

.ObjectTable {
    width: 100%;
}

</style>

<div class="split left">
<h1>Latest Version = new_file</h1>

    Left_Side

</div>

<div class="split right" >
<h1>Previous Version  = old_file</h1>

    Right_Side

</div>
"""


def delete_tags(item):
    output = item.string
    return output


def delete_none_rows(data: pd.DataFrame):
    """
    deleting rows with one value and all others empty
    :param data:
    :return:
    """
    delete_ind = []
    for i, row in data.iterrows():
        num_nones = len(row) - row.count()
        if num_nones >= 0.75 * len(row):
            delete_ind.append(i)
    data.drop(delete_ind, inplace=True)
    data = data.reset_index(drop=True)
    return data


def get_data(path):
    with open(path) as s:
        soup = BeautifulSoup(s, 'html.parser')
    h2_list = soup.find_all('h2')
    df_list = pd.read_html(path)
    h2_list = [delete_tags(item) for item in h2_list]
    style = soup.find_all('style')

    df_dict = {h2_list[i]: df_list[i] for i in range(len(h2_list))}
    return df_dict, style


def create_html_string(df):
    print("creating html file")
    html_string = ''
    for header, data in df.items():
        header_str = f"\n<h2>{header}</h2>\n"
        if isinstance(data, str):
            html_string += header_str
            html_string += f"\n<h4>{data}</h4>\n"
            continue
        for col in data.columns:
            if 'Unnamed' in str(col):
                data.rename(columns={col: " "}, inplace=True)
        string_data = data.to_html()
        if header == 'Enumerations':  # specific cases
            string_data.replace("dataframe", "EnumTable")
        elif header == 'Detector groups/classes':
            string_data.replace("dataframe", "DetectorInfoTable")
        else:
            string_data.replace("dataframe", "ObjectTable")

        html_string += header_str
        html_string += string_data.replace('None', '')

    return html_string

def clean_columns(data,dropped_columns):
    for col in dropped_columns:
        if col in data.columns:
            data.drop(col,axis=1,inplace=True)
            print(f"dropping {col}")
    return data

def data_preprocess(data):
    data = data.astype(object).replace(np.nan, None)
    data = delete_none_rows(data)
    data=clean_columns(data,["Updatable","Description"])

    return data

def main(opt):
    # path_latest = "new_ICD_file.html"
    path_latest = opt.new
    # path_prev = "old_ICD_file.html"
    path_prev = opt.old
    latest_model, style = get_data(path_latest)
    prev_model, _ = get_data(path_prev)
    empty = pd.DataFrame()
    output_data_latest = {}
    output_data_prev = {}

    for header in prev_model:
        # header = 'Stream GstSink configuration'
        data_prev = prev_model.get(header, empty)  # every header has a tables corresponding to it
        data_latest = latest_model.get(header, empty)
        data_prev=data_preprocess(data_prev)
        data_latest=data_preprocess(data_latest)

        assert not data_prev.equals(
            empty), f"Every Header should have a tables corresponding to it, {header} in previous version"

        if data_latest.equals(empty):  # header was deleted in latest deployment
            print("header deleted in latest version", header)
            changed_data_prev = data_prev
            changed_data_latest = "Deleted Header"

        elif data_prev.columns.to_list() != data_latest.columns.to_list():  # check for added columns
            print(f"Latest version has added/deleted columns in the header {header}", len(data_latest), len(data_prev))
            changed_data_latest = data_latest
            changed_data_prev = data_prev

        else:  # test what rows was changed or deleted from prev
            delete_indexes_prev = []
            delete_indexes_latest = []
            for prev_ind, row_prev in enumerate(data_prev.values):
                if row_prev.tolist() in data_latest.values.tolist():
                    latest_ind = data_latest.values.tolist().index(row_prev.tolist())

                    delete_indexes_latest.append(latest_ind)
                    delete_indexes_prev.append(prev_ind)

            data_prev.drop(delete_indexes_prev, inplace=True)
            data_latest.drop(delete_indexes_latest, inplace=True)
            changed_data_latest = data_latest
            changed_data_prev = data_prev
            # else:
            #     print("changes row")
            #     changed_data = pd.concat([changed_data, pd.DataFrame([row_prev], columns=data_latest.columns)],
            #                              ignore_index=True)  # row changed or deleted

        # if not changed_data.equals(pd.DataFrame(columns=data_latest.columns)): # [disabled] do not display empty headers
        output_data_latest[header] = changed_data_latest
        output_data_prev[header] = changed_data_prev

    for header in latest_model:  # check for new added headers in the ICD
        data_prev = prev_model.get(header, empty)
        data_latest = latest_model.get(header, empty)
        data_prev=data_preprocess(data_prev)
        data_latest=data_preprocess(data_latest)

        if data_prev.equals(empty):  # header was deleted in latest deployment
            print("New header added in latest version", header)
            changed_data_latest = data_latest
            changed_data_prev = "Added Header"
            output_data_latest[header] = changed_data_latest
            output_data_prev[header] = changed_data_prev

    html_string_latest = create_html_string(output_data_latest) + "<h3>        END       </h3>"
    html_string_prev = create_html_string(output_data_prev) + "<h3>       END        </h3>"

    final_result = result_file.replace("new_file", opt.new).replace("old_file", opt.old)
    final_result = final_result.replace("Left_Side", html_string_latest).replace("Right_Side", html_string_prev)

    with open('Final_Result.html', "w") as f:
        f.write(final_result)


def open_html():
    print("Opening Final result")
    webbrowser.open_new_tab("ICD_comparison/Final_Result.html")


def get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("-new", required=True, default='new_ICD_file.html', help="path to latest model html")
    parser.add_argument("-old", required=True, default='old_ICD_file.html', help="path to previous model html")

    options = parser.parse_args()
    return options


if __name__ == "__main__":
    args = get_parser()
    main(args)
    open_html()
