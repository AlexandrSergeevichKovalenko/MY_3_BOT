from load_data_from_db import load_data_for_analytics
import asyncio
import pandas as pd

dfs = asyncio.run(load_data_for_analytics(117649764))

all_user_sentences = dfs["sentences"]
print(all_user_sentences)

successful_user_translation = dfs["success"]
print(successful_user_translation)

time_costs_for_user = dfs["progress"]
print(time_costs_for_user)


# in daily_sentences id = in successful_translations sentence_id. It can be joined on this column
#rename the column in 

# Sample DataFrame
#df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6], 'C': [7, 8, 9]})

# Renaming columns
#df.rename(columns={'A': 'X', 'B': 'Y', 'C': 'Z'}, inplace=True)
#print(df)


ds_for_plot = all_user_sentences.join(successful_user_translation, on=)