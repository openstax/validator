# tests_api.py
# Author: drew
# Measures the tradeoffs in timing/accuracy for different configurations of the response parser

import pandas as pd
import time
from itertools import product
import matplotlib as mpl

mpl.use("TkAgg")
from plotnine import *
import requests

# Users params -- where to get the response data and how much of it to sample for testing
BASE_URL = "http://127.0.0.1:5000/validate"
# Local Path 'https://protected-earth-88152.herokuapp.com/validate' #Heroku path

STOPS = [True]
NUMS = ["auto", False, True]
SPELL = [True, False, "auto"]
NONWORDS = [True]
USE_UID = [True]
DATAPATHS = ["./data/expert_grader_valid_100.csv", "./data/alicia_valid.csv"]


# Simple helper function to process the result of the api call into something nice for a pandas dataframe
def do_api_time_call(df_x, stops, nums, spell, nonwords, use_uid):

    response = df_x.free_response
    if not use_uid:
        uid = None
    else:
        uid = df_x.uid

    params = {
        "response": response,
        "uid": uid,
        "remove_stopwords": stops,
        "tag_numeric": nums,
        "spelling_correction": spell,
        "remove_nonwords": nonwords,
    }
    r = requests.get(BASE_URL, params=params)
    D = r.json()
    D = {k: [D[k]] for k in D.keys()}
    return_df = pd.DataFrame(D)

    return return_df


# Iterate through all parser/vocab combinations and get average timing estimates per response
# Then do a 5-fold cross validation to estimate accuracy
print("Starting the test")

df_results = pd.DataFrame()

for datapath, stops, nums, spell, nonwords, use_uid in product(
    DATAPATHS, STOPS, NUMS, SPELL, NONWORDS, USE_UID
):
    # Load the data
    dft = pd.read_csv(datapath)
    dft = dft.rename(columns={'valid': 'valid_input'})
    dft["data"] = datapath
    n_samp = dft.shape[0]

    # Compute the actual features and do the timing computation (normalized per response)
    now = time.time()
    dft_results = dft.apply(lambda x: do_api_time_call(x, stops, nums, spell, nonwords, use_uid), axis=1)
    dft_results = pd.concat(dft_results.values.tolist())
    dft_results = dft_results.reset_index().drop('index', axis=1)
    dft_results = dft.merge(dft_results, left_index=True, right_index=True)
    elapsed_time_total = time.time() - now
    elapsed_time = elapsed_time_total / n_samp

    dft_results["computation_time"] = dft_results["computation_time"].astype(float)
    df_results = df_results.append(dft_results)

df_results = df_results.reset_index()
df_results["pred_correct"] = df_results["valid"] == df_results["valid_input"]

# Compile and display some results
res = (
    df_results.groupby(["data", "tag_numeric_input", "spelling_correction"])
    .agg({"pred_correct": "mean", "computation_time": ["min", "mean", "max"]})
    .reset_index()
)
print(res)

# Plot accuracy by dataset, facet on spelling correction and numerical tagging
res["short_name"] = res["data"].apply(
    lambda x: x.split("/")[-1].split("_")[0] + "_data"
)
res["spelling_str"] = res["spelling_correction"].apply(lambda x: "Spell=" + str(x))
res["number_str"] = res["tag_numeric_input"].apply(lambda x: "Num=" + str(x))
plot_acc = (
    ggplot(res, aes("spelling_correction", "pred_correct"))
    + geom_bar(stat="identity")
    + facet_grid("short_name~number_str")
    + xlab("Spelling Correction")
    + ylab("Prediction Accuracy")
)

# Plot computation time (mean, min, max) for the various cases
df_results["short_name"] = df_results["data"].apply(
    lambda x: x.split("/")[-1].split("_")[0] + "_data"
)
df_results["spelling_str"] = df_results["spelling_correction"].apply(
    lambda x: "Spell=" + str(x)
)
df_results["number_str"] = df_results["tag_numeric_input"].apply(lambda x: "Num=" + str(x))
plot_time = (
    ggplot(df_results, aes("spelling_correction", "1000*computation_time"))
    + geom_violin()
    + facet_grid("short_name~number_str")
    + xlab("Spelling Correction")
    + ylab("Computation Time (msec)")
)

print(plot_acc)
print(plot_time)
