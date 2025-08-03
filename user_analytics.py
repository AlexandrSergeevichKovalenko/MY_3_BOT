from load_data_from_db import load_data_for_analytics
import asyncio
import pandas as pd
import matplotlib
matplotlib.use('Agg') # <-- Встановити неінтерактивний бекенд
import matplotlib.pyplot as plt # <-- Імпортувати pyplot ПІСЛЯ встановлення бекенду
import numpy as np


async def prepare_aggregate_data_by_period_and_draw_analytic_for_user(user_id, start_date, end_date):
    """Loads user analytics data, enriches it with error statistics, 
    calculates session-based metrics, and returns a merged DataFrame."""

    # 🔹 Load data for a specific user (replace this with a loop for all users if needed)
    loop= asyncio.get_running_loop()
    dfs = await loop.run_in_executor(
        None,
        load_data_for_analytics,
        user_id, start_date, end_date
        )

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

async def aggregate_data_for_charts(df: pd.DataFrame, period: str="week") -> pd.DataFrame:
    """
    Агрегує дані для побудови графіків згідно з наданими макетами.
    Враховує унікальність перекладів за парою (session_id, id_for_mistake_table).
    
    Args:
        df (pd.DataFrame): Вхідний DataFrame (ds_for_plot).
        period (str): Період для агрегації: 'day', 'week', 'month', 'quarter', 'year'.

    Returns:
        pd.DataFrame: DataFrame з усіма показниками, необхідними для графіків.
    """

    # 1. Створюємо "очищений" DataFrame, видаляючи дублікати спроб перекладу
    # Це ключовий крок, який реалізує вашу логіку підрахунку
    cleaned_df = df.drop_duplicates(subset=['session_id', 'id_for_mistake_table']).copy()
    cleaned_df['date'] = pd.to_datetime(cleaned_df['date'])

    # 2. Додаємо допоміжні стовпці для зручності агрегації
    cleaned_df['is_successful'] = cleaned_df['score_successed'] >= 80
    cleaned_df['is_unsuccessful'] = cleaned_df['current_score'] > 0
    total_unsuccessful = cleaned_df['is_unsuccessful'].sum()
    print(total_unsuccessful)
    cleaned_df['attempt_1_success'] = (cleaned_df['is_successful']) & (cleaned_df['attempt_successed'] == 1)
    cleaned_df['attempt_2_success'] = (cleaned_df['is_successful']) & (cleaned_df['attempt_successed'] == 2)
    cleaned_df['attempt_3plus_success'] = (cleaned_df['is_successful']) & (cleaned_df['attempt_successed'] >= 3)
    
    # Словник для гнучкого вибору періоду групування
    period_mappers = {
        "day": cleaned_df["date"].dt.to_period("D"),
        "week": cleaned_df["date"].dt.to_period("W"),
        "month": cleaned_df["date"].dt.to_period("M"),
        "quarter": cleaned_df["date"].dt.to_period("Q"),
        "year": cleaned_df["date"].dt.to_period("Y")
    }
    if period not in period_mappers:
        raise ValueError("Used incorrected grouped period. Please use 'day', 'week', 'month', 'quarter' або 'year'.")
    
    grouper = period_mappers[period]
    # 3. Агрегація показників для графіків з "очищених" даних
    sentence_agg = cleaned_df.groupby(grouper).agg(
        # Показники для Графіку 1
        total_translations = ("session_id", "count"),
        successful_translations = ('is_successful', 'sum'),
        unsuccessful_translations = ('is_unsuccessful', 'sum'),
        # Показники для Графіку 2
        success_on_1st_attempt=('attempt_1_success', 'sum'),
        success_on_2nd_attempt=('attempt_2_success', 'sum'),
        success_on_3plus_attempt=('attempt_3plus_success', 'sum'),
    )


    # 4. Окремо агрегуємо час, щоб уникнути подвійного підрахунку
    session_unique_df = df.drop_duplicates(subset=['date', 'session_id'])
    session_agg = session_unique_df.groupby(grouper).agg(
        total_time_spent_sec = ('session_duration', 'sum')
    )

    # 5. Об'єднуємо все в одну таблицю
    df_grouped = pd.concat([sentence_agg, session_agg], axis=1).fillna(0)

    # 6. Розраховуємо фінальні відносні показники (долі, середній час)
    df_grouped['total_time_spent_min'] = round(df_grouped['total_time_spent_sec']/ 60, 2)
    df_grouped['avg_min_per_translation'] = df_grouped.apply(
        lambda row: round(row["total_time_spent_min"] / row["total_translations"], 2) if row["total_translations"] > 0 else 0,
        axis=1
    )

    # Розрахунок долей для Графіку 1
    df_grouped['share_successful'] = df_grouped.apply(
        lambda row: round(row["successful_translations"]/ row["total_translations"] * 100, 1) if row["successful_translations"] > 0 else 0,
        axis=1
    )
    df_grouped['share_unsuccessful'] = 100 - df_grouped['share_successful']

    # Видаляємо непотрібний стовпець
    df_grouped.drop(columns=['total_time_spent_sec'], inplace=True)

    df_grouped.to_excel("grouped_ds.xlsx", index=True)

    return df_grouped


def plot_user_analytics(ax, df, title, chart_type='time_and_success'):
    """
    Малює один аналітичний графік на вказаній осі (ax).

    Args:
        ax (matplotlib.axes.Axes): Вісь, на якій потрібно малювати.
        df (pd.DataFrame): Агреговані дані для побудови.
        title (str): Заголовок для графіка.
        chart_type (str): Тип графіка ('time_and_success' або 'attempts').
    """
    # Готуємо дані для осі X
    x_labels = df.index.astype(str)
    x = np.arange(len(x_labels)) 

    if chart_type == 'time_and_success':
        # --- Графік 1: Доля успішних/неуспішних і час ---

        # Малюємо стовпчасту діаграму
        ax.bar(x, df['successful_translations'], width=0.6, label="Successful(>=80)", color="g")
        ax.bar(x, df['unsuccessful_translations'], width=0.6, bottom=df['successful_translations'], label="Unsuccessful(<80)", color="r")
        ax.set_ylabel("Number of translations")
        ax.legend(loc="upper left")

        # Створюємо другу вісь Y для графіка часу
        ax2 = ax.twinx()
        ax2.plot(x, df['avg_min_per_translation'], color="b", marker='o', linestyle='--', label= "Average time (min) per each translation")
        ax2.set_ylabel("Minutes", color="b")
        ax2.tick_params(axis="y", labelcolor="b")
        ax2.legend(loc="upper right")
    
    elif chart_type == "attempts":
        # --- Графік 2: Аналіз за спробами ---
        ax.bar(x, df['success_on_1st_attempt'], width=0.6, label="Success from the 1 try", color='#2ca02c')
        ax.bar(x, df['success_on_2nd_attempt'], width=0.6, label="Success from the 2 try", 
                bottom=df['success_on_1st_attempt'],color='#ff7f0e')
        bottom_3 = df['success_on_1st_attempt'] +df['success_on_2nd_attempt']
        ax.bar(x, df['success_on_3plus_attempt'], width=0.6, bottom=bottom_3,
            label='Success from the 3 try', color='#1f77b4')
        bottom_4 = bottom_3 + df['success_on_3plus_attempt']
        ax.bar(x, df['unsuccessful_translations'], width=0.6, bottom=bottom_4,
            label='Неуспішні', color='#d62728') # червоний
        
        ax.set_ylabel("Number of translations")
        ax.legend(loc="best")

    ax.set_title(title, fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=45, ha="right")
    ax.grid(True,axis="x", linestyle="--", alpha=0.7)
    

async def create_analytics_figure_async(daily_data, weekly_data, user_id):
    """
    Async shell for the creation of the bar-chart
    """
    loop = asyncio.get_running_loop()
    
    fig, axes = plt.subplots(2,1, figsize=(14,12))

    await loop.run_in_executor(
        None,
        plot_user_analytics,
        axes[0],
        daily_data.tail(7),
        "Daily Analytics: Time and Success",
        'time_and_success'
    )

    await loop.run_in_executor(
        None,
        plot_user_analytics,
        axes[1],
        weekly_data.tail(4),
        "Weekly Analytics: Tries",
        "attempts"
    )

            
    # Додаємо загальний заголовок
    fig.suptitle(f"The whole Analytics for the user {user_id}", fontsize=16)

    # Робимо вигляд компактнішим
    plt.tight_layout(rect=[0, 0, 1, 0.96]) # Залишаємо місце для suptitle

    #save in file to send it to telegram
    figure_path = f"analytics_{user_id}.png"
    fig.savefig(figure_path)
    plt.close(fig)

    return figure_path




