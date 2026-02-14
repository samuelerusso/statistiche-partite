import streamlit as st
import pandas as pd
import unicodedata

NUM_RECENT_FORM = 5

# ==============================
# NORMALIZZAZIONE NOMI SQUADRE
# ==============================
def normalize_team_name(name):
    if pd.isna(name):
        return ""
    name = str(name).strip().lower()
    name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
    return name

# ==============================
# CARICA CSV
# ==============================
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("partite.csv")
    except FileNotFoundError:
        st.error("❌ File Partite.csv non trovato nel repository GitHub")
        st.stop()

    # pulizia colonne
    df.columns = df.columns.str.strip().str.lower()

    # rinomina colonne gol
    rename_map = {
        "fthome": "gol_casa",
        "ftaway": "gol_trasferta",
        "hometeam": "casa",
        "awayteam": "trasferta"
    }
    df = df.rename(columns=rename_map)

    # controlla colonne obbligatorie
    required_cols = ["casa", "trasferta", "gol_casa", "gol_trasferta"]
    for col in required_cols:
        if col not in df.columns:
            st.error(f"❌ Colonna obbligatoria mancante nel CSV: {col}")
            st.write("Colonne trovate nel file:", df.columns.tolist())
            st.stop()

    # normalizza nomi squadre
    df['casa_norm'] = df['casa'].apply(normalize_team_name)
    df['trasferta_norm'] = df['trasferta'].apply(normalize_team_name)

    return df

# ==============================
# CALCOLO STATISTICHE E PRONOSTICI
# ==============================
def calcola_statistiche(df_all, squadra1, squadra2):
    squadra1_norm = normalize_team_name(squadra1)
    squadra2_norm = normalize_team_name(squadra2)

    # scontri diretti
    df1 = df_all[
        ((df_all['casa_norm']==squadra1_norm) & (df_all['trasferta_norm']==squadra2_norm)) |
        ((df_all['casa_norm']==squadra2_norm) & (df_all['trasferta_norm']==squadra1_norm))
    ]

    if df1.empty:
        return None

    tot_partite = len(df1)

    vittorie1 = ((df1['gol_casa'] > df1['gol_trasferta']) & (df1['casa_norm']==squadra1_norm)).sum() + \
                ((df1['gol_trasferta'] > df1['gol_casa']) & (df1['trasferta_norm']==squadra1_norm)).sum()

    vittorie2 = ((df1['gol_casa'] > df1['gol_trasferta']) & (df1['casa_norm']==squadra2_norm)).sum() + \
                ((df1['gol_trasferta'] > df1['gol_casa']) & (df1['trasferta_norm']==squadra2_norm)).sum()

    pareggi = (df1['gol_casa'] == df1['gol_trasferta']).sum()

    gol1_fatti = df1.apply(lambda r: r['gol_casa'] if r['casa_norm']==squadra1_norm else r['gol_trasferta'], axis=1).mean()
    gol2_fatti = df1.apply(lambda r: r['gol_casa'] if r['casa_norm']==squadra2_norm else r['gol_trasferta'], axis=1).mean()
    gol1_subiti = df1.apply(lambda r: r['gol_trasferta'] if r['casa_norm']==squadra1_norm else r['gol_casa'], axis=1).mean()
    gol2_subiti = df1.apply(lambda r: r['gol_trasferta'] if r['casa_norm']==squadra2_norm else r['gol_casa'], axis=1).mean()

    # forma recente
    df_s1 = df_all[(df_all['casa_norm']==squadra1_norm) | (df_all['trasferta_norm']==squadra1_norm)].tail(NUM_RECENT_FORM)
    df_s2 = df_all[(df_all['casa_norm']==squadra2_norm) | (df_all['trasferta_norm']==squadra2_norm)].tail(NUM_RECENT_FORM)

    forma1 = ((df_s1['gol_casa'] > df_s1['gol_trasferta']) & (df_s1['casa_norm']==squadra1_norm)).sum() + \
             ((df_s1['gol_trasferta'] > df_s1['gol_casa']) & (df_s1['trasferta_norm']==squadra1_norm)).sum()
    forma2 = ((df_s2['gol_casa'] > df_s2['gol_trasferta']) & (df_s2['casa_norm']==squadra2_norm)).sum() + \
             ((df_s2['gol_trasferta'] > df_s2['gol_casa']) & (df_s2['trasferta_norm']==squadra2_norm)).sum()

    # percentuali
    perc1 = vittorie1 / tot_partite * 100
    percX = pareggi / tot_partite * 100
    perc2 = vittorie2 / tot_partite * 100

    risultato_finale = max([("1", perc1), ("X", percX), ("2", perc2)], key=lambda x: x[1])[0]

    if perc1 + percX > perc2:
        doppia_finale = "1X"
    elif perc2 + percX > perc1:
        doppia_finale = "X2"
    else:
        doppia_finale = "12"

    media_gol_tot = gol1_fatti + gol2_fatti
    if media_gol_tot > 2.5:
        over_finale = "OVER 2.5"
    elif media_gol_tot > 1.5:
        over_finale = "OVER 1.5"
    else:
        over_finale = "OVER 0.5"

    if gol1_fatti > 0.8 and gol2_fatti > 0.8:
        goal_finale = "GOAL"
    else:
        goal_finale = "NOGOAL"

    # ==============================
    # STATISTICHE COMPLETE (tutte le colonne numeriche)
    # ==============================
    numeric_cols = df_all.select_dtypes(include=['number']).columns.tolist()
    stats_complete = []
    df_s1_all = df_all[(df_all['casa_norm']==squadra1_norm) | (df_all['trasferta_norm']==squadra1_norm)]
    df_s2_all = df_all[(df_all['casa_norm']==squadra2_norm) | (df_all['trasferta_norm']==squadra2_norm)]

    for col in numeric_cols:
        try:
            media_scontri = df1[col].mean()
            media_s1 = df_s1_all[col].mean()
            media_s2 = df_s2_all[col].mean()
            superiore = squadra1 if media_s1 > media_s2 else squadra2

            stats_complete.append({
                "Statistica": col,
                squadra1: round(media_s1,2),
                squadra2: round(media_s2,2),
                "Scontri Diretti": round(media_scontri,2),
                "Superiore": superiore
            })
        except:
            continue

    stats_df = pd.DataFrame(stats_complete)

    return {
        "tot_partite": tot_partite,
        "vittorie1": vittorie1,
        "vittorie2": vittorie2,
        "pareggi": pareggi,
        "gol1_fatti": gol1_fatti,
        "gol1_subiti": gol1_subiti,
        "gol2_fatti": gol2_fatti,
        "gol2_subiti": gol2_subiti,
        "forma1": forma1,
        "forma2": forma2,
        "perc1": perc1,
        "percX": percX,
        "perc2": perc2,
        "risultato_finale": risultato_finale,
        "doppia_finale": doppia_finale,
        "over_finale": over_finale,
        "goal_finale": goal_finale,
        "stats_complete": stats_df
    }

# ==============================
# STREAMLIT UI
# ==============================
st.title("⚽ Analizzatore Partite PRO")

df_all = load_data()
squadre = sorted(set(df_all['casa'].unique()).union(set(df_all['trasferta'].unique())))

squadra_casa = st.selectbox("Squadra Casa", squadre)
squadra_trasferta = st.selectbox("Squadra Trasferta", squadre)

if st.button("Analizza"):
    risultato = calcola_statistiche(df_all, squadra_casa, squadra_trasferta)

    if risultato is None:
        st.warning("❌ Nessuna partita trovata tra queste squadre")
    else:
        st.subheader("📊 Statistiche Base")
        st.write(f"Totale partite: {risultato['tot_partite']}")
        st.write(f"Vittorie {squadra_casa}: {risultato['vittorie1']}")
        st.write(f"Vittorie {squadra_trasferta}: {risultato['vittorie2']}")
        st.write(f"Pareggi: {risultato['pareggi']}")
        st.write(f"Gol medi fatti/subiti {squadra_casa}: {risultato['gol1_fatti']:.2f}/{risultato['gol1_subiti']:.2f}")
        st.write(f"Gol medi fatti/subiti {squadra_trasferta}: {risultato['gol2_fatti']:.2f}/{risultato['gol2_subiti']:.2f}")
        st.write(f"Forma ultime {NUM_RECENT_FORM} partite: {squadra_casa}={risultato['forma1']} pts | {squadra_trasferta}={risultato['forma2']} pts")
        st.write(f"Percentuale vittorie {squadra_casa}: {risultato['perc1']:.1f}% | Pareggi: {risultato['percX']:.1f}% | Vittorie {squadra_trasferta}: {risultato['perc2']:.1f}%")

        st.subheader("🎯 Pronostico Finale")
        st.write(f"Risultato consigliato: {risultato['risultato_finale']}")
        st.write(f"Doppia chance: {risultato['doppia_finale']}")
        st.write(f"Over consigliato: {risultato['over_finale']}")
        st.write(f"Goal/NoGoal: {risultato['goal_finale']}")

        st.subheader("📈 Statistiche Dettagliate")
        # Ciclo tutte le statistiche numeriche calcolate
        for stat in risultato["stats_complete"].to_dict(orient="records"):
            st.write(f"**{stat['Statistica']}** - {squadra_casa}: {stat[squadra_casa]}, {squadra_trasferta}: {stat[squadra_trasferta]}, Scontri diretti: {stat['Scontri Diretti']}, Superiore: {stat['Superiore']}")


