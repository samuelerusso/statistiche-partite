# app.py
import pandas as pd
import streamlit as st

# ==============================
# CONFIGURAZIONE
# ==============================
CSV_FILE = "Partite.csv"
NUM_RECENT_FORM = 5
YEARS_BACK = 10

# ==============================
# CARICA CSV PARTITE
# ==============================
@st.cache_data
def load_data():
    df = pd.read_csv(CSV_FILE, low_memory=False)
    df = df.loc[:, ~df.columns.duplicated()]  # Rimuove colonne duplicate
    if 'MatchDate' in df.columns:
        df = df.rename(columns={"MatchDate": "data"})
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df = df[df['data'].dt.year >= df['data'].dt.year.max() - YEARS_BACK + 1]
    df = df.rename(columns={
        "HomeTeam": "squadra_casa",
        "AwayTeam": "squadra_trasferta",
        "FTHome": "gol_casa",
        "FTAway": "gol_trasferta",
        "HomeShots": "tiri_casa",
        "AwayShots": "tiri_trasferta",
        "HomeYellow": "gialli_casa",
        "AwayYellow": "gialli_trasferta",
        "HomeRed": "rossi_casa",
        "AwayRed": "rossi_trasferta"
    })
    df['casa_norm'] = df['squadra_casa'].apply(normalize_team)
    df['trasferta_norm'] = df['squadra_trasferta'].apply(normalize_team)
    return df

# ==============================
# NORMALIZZAZIONE NOMI SQUADRE
# ==============================
def normalize_team(name):
    name = str(name).lower()
    for prefix in ["as ", "ssc ", "fc "]:
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name.strip()

# ==============================
# FUNZIONE STATISTICHE E PRONOSTICI
# ==============================
def calcola_statistiche(df_all, squadra1, squadra2):
    squadra1_norm = normalize_team(squadra1)
    squadra2_norm = normalize_team(squadra2)

    df1 = df_all[
        ((df_all['casa_norm'] == squadra1_norm) & (df_all['trasferta_norm'] == squadra2_norm)) |
        ((df_all['casa_norm'] == squadra2_norm) & (df_all['trasferta_norm'] == squadra1_norm))
    ]

    if df1.empty:
        return None

    tot_partite = len(df1)
    vittorie1 = len(df1[((df1['casa_norm']==squadra1_norm) & (df1['gol_casa']>df1['gol_trasferta'])) |
                         ((df1['trasferta_norm']==squadra1_norm) & (df1['gol_trasferta']>df1['gol_casa']))])
    vittorie2 = len(df1[((df1['casa_norm']==squadra2_norm) & (df1['gol_casa']>df1['gol_trasferta'])) |
                         ((df1['trasferta_norm']==squadra2_norm) & (df1['gol_trasferta']>df1['gol_casa']))])
    pareggi = tot_partite - vittorie1 - vittorie2

    # Media gol fatti/subiti
    gol1_fatti = df1.apply(lambda r: r['gol_casa'] if r['casa_norm']==squadra1_norm else r['gol_trasferta'], axis=1).mean()
    gol1_subiti = df1.apply(lambda r: r['gol_trasferta'] if r['casa_norm']==squadra1_norm else r['gol_casa'], axis=1).mean()
    gol2_fatti = df1.apply(lambda r: r['gol_casa'] if r['casa_norm']==squadra2_norm else r['gol_trasferta'], axis=1).mean()
    gol2_subiti = df1.apply(lambda r: r['gol_trasferta'] if r['casa_norm']==squadra2_norm else r['gol_casa'], axis=1).mean()

    # Forma recente
    df_recent1 = df_all[(df_all['casa_norm']==squadra1_norm) | (df_all['trasferta_norm']==squadra1_norm)].sort_values('data', ascending=False).head(NUM_RECENT_FORM)
    df_recent2 = df_all[(df_all['casa_norm']==squadra2_norm) | (df_all['trasferta_norm']==squadra2_norm)].sort_values('data', ascending=False).head(NUM_RECENT_FORM)
    forma1 = df_recent1.apply(lambda r: (3 if (r['gol_casa']>r['gol_trasferta'] and r['casa_norm']==squadra1_norm) or (r['gol_trasferta']>r['gol_casa'] and r['trasferta_norm']==squadra1_norm) else 1 if r['gol_casa']==r['gol_trasferta'] else 0), axis=1).sum()
    forma2 = df_recent2.apply(lambda r: (3 if (r['gol_casa']>r['gol_trasferta'] and r['casa_norm']==squadra2_norm) or (r['gol_trasferta']>r['gol_casa'] and r['trasferta_norm']==squadra2_norm) else 1 if r['gol_casa']==r['gol_trasferta'] else 0), axis=1).sum()

    # Pronostici
    pron_risultato = {'1': vittorie1/tot_partite*100, 'X': pareggi/tot_partite*100, '2': vittorie2/tot_partite*100}
    pron_doppia = {'1X': pron_risultato['1']+pron_risultato['X'], 'X2': pron_risultato['X']+pron_risultato['2'], '12': pron_risultato['1']+pron_risultato['2']}
    over_05 = len(df1[df1['gol_casa']+df1['gol_trasferta']>0])/tot_partite*100
    over_15 = len(df1[df1['gol_casa']+df1['gol_trasferta']>1])/tot_partite*100
    over_25 = len(df1[df1['gol_casa']+df1['gol_trasferta']>2])/tot_partite*100
    goal1 = len(df1[df1.apply(lambda r: (r['gol_casa']>0 if r['casa_norm']==squadra1_norm else r['gol_trasferta']>0), axis=1)])/tot_partite*100
    goal2 = len(df1[df1.apply(lambda r: (r['gol_casa']>0 if r['casa_norm']==squadra2_norm else r['gol_trasferta']>0), axis=1)])/tot_partite*100
    goal_goal = len(df1[df1.apply(lambda r: (r['gol_casa']>0 and r['gol_trasferta']>0), axis=1)])/tot_partite*100

    # Pronostico finale consigliato
    risultato_finale = max(pron_risultato, key=pron_risultato.get)
    doppia_finale = max(pron_doppia, key=pron_doppia.get)
    if over_25 > 60:
        over_finale = "Over2.5"
    elif over_15 > 60:
        over_finale = "Over1.5"
    else:
        over_finale = "Over0.5"
    goal_finale = "GOAL" if goal_goal>60 else "NOGOAL"

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
        "pron_risultato": pron_risultato,
        "pron_doppia": pron_doppia,
        "over_05": over_05,
        "over_15": over_15,
        "over_25": over_25,
        "goal1": goal1,
        "goal2": goal2,
        "goal_goal": goal_goal,
        "risultato_finale": risultato_finale,
        "doppia_finale": doppia_finale,
        "over_finale": over_finale,
        "goal_finale": goal_finale
    }

# ==============================
# STREAMLIT INTERFACE
# ==============================
st.title("📊 Pronostici Partite Calcio")

df_all = load_data()
squadre = sorted(list(set(df_all['squadra_casa'].unique()) | set(df_all['squadra_trasferta'].unique())))

squadra_casa = st.selectbox("Squadra Casa:", squadre)
squadra_trasferta = st.selectbox("Squadra Trasferta:", squadre)

if st.button("Calcola pronostico"):
    risultato = calcola_statistiche(df_all, squadra_casa, squadra_trasferta)
    if risultato is None:
        st.warning("❌ Nessuna partita trovata tra queste squadre")
    else:
        st.subheader(f"📊 Statistiche e pronostico {squadra_casa} vs {squadra_trasferta}")
        st.write(f"Totale partite: {risultato['tot_partite']}")
        st.write(f"{squadra_casa} vittorie: {risultato['vittorie1']}")
        st.write(f"{squadra_trasferta} vittorie: {risultato['vittorie2']}")
        st.write(f"Pareggi: {risultato['pareggi']}")
        st.write(f"{squadra_casa} media gol fatti/subiti: {risultato['gol1_fatti']:.1f}/{risultato['gol1_subiti']:.1f}")
        st.write(f"{squadra_trasferta} media gol fatti/subiti: {risultato['gol2_fatti']:.1f}/{risultato['gol2_subiti']:.1f}")
        st.write(f"Forma ultime {NUM_RECENT_FORM} partite: {squadra_casa}={risultato['forma1']} pts | {squadra_trasferta}={risultato['forma2']} pts")

        st.subheader("🎯 Pronostici probabilistici")
        st.write(f"Risultato secco: 1={risultato['pron_risultato']['1']:.1f}% | X={risultato['pron_risultato']['X']:.1f}% | 2={risultato['pron_risultato']['2']:.1f}%")
        st.write(f"Doppia chance: 1X={risultato['pron_doppia']['1X']:.1f}% | X2={risultato['pron_doppia']['X2']:.1f}% | 12={risultato['pron_doppia']['12']:.1f}%")
        st.write(f"Over/Under gol: Over0.5={risultato['over_05']:.1f}% | Over1.5={risultato['over_15']:.1f}% | Over2.5={risultato['over_25']:.1f}%")
        st.write(f"Goal/NoGoal: {squadra_casa} GOAL={risultato['goal1']:.1f}% | {squadra_trasferta} GOAL={risultato['goal2']:.1f}% | Entrambe segnano={risultato['goal_goal']:.1f}%")

        st.subheader("🏆 Pronostico finale consigliato")
        st.write(f"Risultato secco: {risultato['risultato_finale']}")
        st.write(f"Doppia chance: {risultato['doppia_finale']}")
        st.write(f"Over/Under: {risultato['over_finale']}")
        st.write(f"Goal/NoGoal: {risultato['goal_finale']}")
