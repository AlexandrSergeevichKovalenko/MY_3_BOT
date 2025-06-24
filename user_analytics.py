from load_data_from_db import load_data_for_analytics
import asyncio
import pandas as pd


async def prepare_aggregate_data_by_period_and_draw_analytic_for_user(period: str = 'week'):
    """Loads user analytics data, enriches it with error statistics, 
    calculates session-based metrics, and returns a merged DataFrame."""

    # 🔹 Load data for a specific user (replace this with a loop for all users if needed)
    dfs = await load_data_for_analytics(117649764)

    all_user_sentences = dfs["sentences"].copy()
    all_user_sentences.rename(columns={"id": "sentence_id"}, inplace=True)
    not_succeded_sentences = dfs["not_succesed_attempts"].copy()
    not_succeded_sentences.rename(columns={
        "attempt":"attempt_not_succeded"
    }, inplace=True)

    successful_user_translation = dfs["success"].copy()
    
    time_costs_for_user = dfs["progress"]
    still_mistakes = dfs["mistakes"].copy()

    # 🔹 Rename columns for joining (так как в таблице detailed_mistakes Под sentence_id На самом деле находится id_for_mistake_table)
    still_mistakes.rename(columns={
        "sentence_id": "id_for_mistake_table",
        "score": "current_score"
    }, inplace=True)

    successful_user_translation.rename(columns={
        "sentence_id": "id_for_mistake_table"
    }, inplace=True)   

    
    # 🔹 Align date formats for join (set time to 00:00:00)
    #still_mistakes["added_data"] = pd.to_datetime(still_mistakes["added_data"]).dt.floor("D")
    all_user_sentences["date"] = pd.to_datetime(all_user_sentences["date"]).dt.floor("D")
    

    successful_user_translation.rename(columns={
        "date": "date_of_success"
    }, inplace=True)
    successful_user_translation["date_of_success"] = pd.to_datetime(successful_user_translation["date_of_success"].dt.floor("D"))
    
    # 🔹 Merge base user sentence data
    ds_for_plot = all_user_sentences.merge(
        successful_user_translation,
        on="id_for_mistake_table", 
        how="left"
    )

    ds_for_plot = ds_for_plot.merge(
        time_costs_for_user[["session_id", "username", "start_time", "end_time"]],
        on="session_id", 
        how="left"
        )

    # 🔹 Rename, compute durations
    ds_for_plot["start_session"] = ds_for_plot["start_time"]
    ds_for_plot["end_session"] = ds_for_plot["end_time"]
    ds_for_plot.drop(["start_time", "end_time"], axis="columns", inplace=True)

    ds_for_plot["session_duration"] = (
        ds_for_plot["end_session"] - ds_for_plot["start_session"]
    ).dt.total_seconds()

    # groupby("date"): группирует все строки по дате
    # ["sentence_id"]: выбирает колонку sentence_id в каждой группе
    # .count(): считает количество непустых sentence_id в каждой группе
    # transform("count"): возвращает столько же строк, сколько в исходном DataFrame, с одинаковым значением для всех строк той же группы
    # count() возвращает одну строку на группу (например: date | count)
    # but transform("count") возвращает одну строку на каждую запись, и позволяет использовать это значение внутри оригинального DataFrame — например, для деления
    ds_for_plot["sentences_in_session"] = ds_for_plot.groupby(["date", "session_id"])["sentence_id"].transform("count")

    ds_for_plot["avg_min_sentence_session"] = round(
        ((ds_for_plot["session_duration"] / ds_for_plot["sentences_in_session"]) / 60), 2
    )

    # 🔹 Rename column for clarity
    ds_for_plot.rename(
        columns={
            "attempt": "attempt_successed",
            "score": "score_successed"}, 
        inplace=True
        )

    ds_for_plot["sentences_in_day"] = ds_for_plot.groupby("date")["sentence_id"].transform("count")
    session_durations = ds_for_plot.drop_duplicates("session_id")[["date", "session_id", "session_duration"]]
    total_time_per_day = session_durations.groupby("date")["session_duration"].sum()
    
    ds_for_plot = ds_for_plot.merge(
    total_time_per_day.rename("spent_time_per_day"),
    on="date",
    how="left"
    )

    ds_for_plot["avg_min_sentence_day"] = round(
        ((ds_for_plot["spent_time_per_day"] / ds_for_plot["sentences_in_day"]) / 60), 2
    )

    ds_for_plot = ds_for_plot.merge(
    not_succeded_sentences,
    on=["id_for_mistake_table", "user_id"],
    how="left"
    )

    # 5. Исправить колонку ds_for_plot["has_mistake"] = ds_for_plot["mistake_count"].notna() Так как у нас больше не будет Колонки mistake_count


    # 🔹 Merge with mistake statistics
    ds_for_plot = ds_for_plot.merge(
        still_mistakes,
        on=["id_for_mistake_table"],
        how="left"
    )

    # 🔹 Optional: add flag whether the sentence had a mistake
    ds_for_plot["user_stil_has_mistake"] = ds_for_plot["attempt_not_succeded"].notna()


    # 🔹 Export to Excel (optional)
    ds_for_plot.to_excel("test_ds.xlsx", index=False)

    return ds_for_plot


if __name__ == "__main__":
    result = asyncio.run(prepare_aggregate_data_by_period_and_draw_analytic_for_user())

