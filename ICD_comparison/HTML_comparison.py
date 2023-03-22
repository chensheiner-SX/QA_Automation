import pandas as pd
import requests
from bs4 import BeautifulSoup
import numpy as np
import argparse
import webbrowser


result_file="""
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

def delete_none_rows(data:pd.DataFrame):
    """
    deleting rows with one value and all other empty
    :param data:
    :return:
    """
    delete_ind=[]
    for i, row in data.iterrows():
        num_nones=len(row)-row.count()
        if num_nones>=0.75*len(row):
            delete_ind.append(i)
    data.drop(delete_ind,inplace=True)
    data=data.reset_index(drop=True)
    return data

def get_data(path):
    with open(path) as s:
        soup = BeautifulSoup(s, 'html.parser')
    h2_list = soup.find_all('h2')
    df_list = pd.read_html(path)
    h2_list = [delete_tags(item) for item in h2_list]
    style= soup.find_all('style')

    df_dict = {h2_list[i]: df_list[i] for i in range(len(h2_list))}
    return df_dict,style


def create_html_string(df):
    print("creating html file")
    html_string = ''
    for header, data in df.items():
        header_str = f"\n<h2>{header}</h2>\n"
        for col in data.columns:
            if 'Unnamed' in str(col):
                data.rename(columns={col: " "}, inplace=True)
        string_data = data.to_html()
        if header == 'Enumerations':  # spesific cases
            string_data.replace("dataframe", "EnumTable")
        elif header == 'Detector groups/classes':
            string_data.replace("dataframe", "DetectorInfoTable")
        else:
            string_data.replace("dataframe", "ObjectTable")

        html_string += header_str
        html_string += string_data.replace('None', '')

    return html_string



def main(opt):
    # path_latest = "new_ICD_file.html"
    path_latest = opt.new
    # path_prev = "old_ICD_file.html"
    path_prev =  opt.old
    latest_model,style = get_data(path_latest)
    prev_model,_ = get_data(path_prev)
    empty = pd.DataFrame()
    output_data_latest = {}
    output_data_prev = {}
    output_details = {}
    for header in prev_model:
        # header = 'Stream GstSink configuration'

        data_prev = prev_model.get(header, empty) # every header has a tables corresponding to it
        data_latest = latest_model.get(header, empty)
        data_prev = data_prev.astype(object).replace(np.nan, None)
        data_latest = data_latest.astype(object).replace(np.nan, None)
        data_latest=delete_none_rows(data_latest)
        data_prev=delete_none_rows(data_prev)

        assert not data_prev.equals(empty), f"Every Header should have a tables corresponding to it, {header} in previous version"
        changed_data_latest = pd.DataFrame(columns=data_latest.columns)
        changed_data_prev = pd.DataFrame(columns=data_prev.columns)
        # if data_prev.equals(data_latest): # same data
        #     print(f"same data in header: {header}")
        if data_latest.equals(empty):  # header was deleted in latest deployment
            print("header deleted in latest version", header)
            changed_data_prev=data_prev
            # changed_data_latest = pd.DataFrame([header,"Deleted Colum"],columns=["Header","Info"])
        elif 1 == 2:  # TODO header was added in latest version
            pass
        elif data_prev.columns.to_list() != data_latest.columns.to_list():  # check for added columns
            print(f"Latest version hass added/deleted columns in the header {header}",len(data_latest),len(data_prev))
            changed_data_latest=data_latest
            changed_data_prev=data_prev
            # if not all([col in data_latest.columns.to_list() for col in data_prev.columns.to_list()]): # some col was deleted
            #     output_data[header] = pd.concat([data_latest,data_latest.add_suffix('_previous')],axis=1)
        else:  # test what rows was changed or deleted from prev
            delete_indexs_prev = []
            delete_indexs_latest = []
            for prev_ind, row_prev in enumerate(data_prev.values):
                # print("\n\n", prev_ind)
                if row_prev.tolist() in data_latest.values.tolist():
                    latest_ind = data_latest.values.tolist().index(row_prev.tolist())
                    # if latest_ind in delete_indexs_latest: # Solution for duplicates of rows # TODO its plaster
                    #     latest_ind = data_latest[latest_ind:].values.tolist().index(row_prev.tolist())
                    delete_indexs_latest.append(latest_ind)
                    delete_indexs_prev.append(prev_ind)
                    # print(latest_ind)
                    # if latest_ind!=prev_ind: # TODO TO-NOTE i(chen) am not recording change in order of rows in a single table or reorder of tables
            # print(header,delete_indexs_prev,delete_indexs_latest)
            data_prev.drop(delete_indexs_prev,inplace=True)
            data_latest.drop(delete_indexs_latest,inplace=True)
            changed_data_latest=data_latest
            changed_data_prev=data_prev
                # else:
                #     print("changes row")
                #     changed_data = pd.concat([changed_data, pd.DataFrame([row_prev], columns=data_latest.columns)],
                #                              ignore_index=True)  # row changed or deleted

        # if not changed_data.equals(pd.DataFrame(columns=data_latest.columns)): # [disabled] do not display empty headers
        output_data_latest[header] = changed_data_latest
        output_data_prev[header] = changed_data_prev

    html_string_latest=create_html_string(output_data_latest)
    html_string_prev=create_html_string(output_data_prev)


    final_result=result_file.replace("new_file",opt.new).replace("old_file",opt.old)
    final_result=final_result.replace("Left_Side",html_string_latest).replace("Right_Side",html_string_prev)

    with open('ICD_comparison/Final_Result.html', "w") as f:
        f.write(final_result)
    # with open('ICD_comparison/new.html', "w") as f:
    #     f.write(str(style[0])+f"\n<h1>Latest Version</h1>\n"+html_string_latest)
    #
    # with open('ICD_comparison/old.html', "w") as f:
    #     f.write(str(style[0])+f"\n<h1>Previous Version</h1>\n"+html_string_prev)

def open_html():
    print("Openning Final result")
    webbrowser.open_new_tab("ICD_comparison/Final_Result.html")


def get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("-new", required=True,default='new_ICD_file.html', help="path to latest model html")
    parser.add_argument("-old",required=True,default='old_ICD_file.html',  help="path to previous model html")

    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args=get_parser()
    main(args)
    open_html()
