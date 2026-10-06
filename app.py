import streamlit as st
import random
import pandas as pd
import numpy as np
import plotly.express as px
import os

# --- page setup and styling ---

st.set_page_config(
    page_title="Collector's Dilemma",
    layout="wide",
    initial_sidebar_state="collapsed"
)

custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');

body {
    font-family: 'Roboto', sans-serif;
}

[data-testid="stHeader"] { background-color: rgba(0, 0, 0, 0) !important; }

/* hide the streamlit menu */
header [data-testid="stMenu"], header [role="menu"] {
    visibility: hidden !important;
    display: none !important;
}

/* background */
.stApp {
    background: linear-gradient(120deg, #f9e4f7 0%, #fad0c4 40%, #a1c4fd 100%) !important;
    min-height: 100vh;
}

/* no white box behind the content */
[data-testid="stAppViewContainer"] .main .block-container {
    background: transparent !important;
    box-shadow: none !important;
    border: none !important;
    padding: 32px;
}

/* spread out the radio buttons */
[data-testid="stRadio"][aria-orientation="horizontal"] > div {
    display: flex;
    justify-content: space-around;
    width: 100%;
}

h1, h2, h3 {
    font-weight: 700;
    color: #00796b;
    text-align: center;
}

.stButton > button {
    border-radius: 12px;
    background: linear-gradient(90deg, #9ae6b4, #90cdf4);
    color: #2d3748;
    font-weight: 700;
    box-shadow: 0 4px 14px 0 rgba(0,0,0,0.09);
    border: none;
    padding: 10px 20px;
    transition: all 0.3s ease;
}
.stButton > button:hover {
    transform: translateY(-2px);
    background: linear-gradient(90deg, #90cdf4, #9ae6b4);
    color: #00796b;
    box-shadow: 0 6px 20px 0 rgba(0,121,107,0.27);
}
.gem-collected {
    background: linear-gradient(135deg, #81e6d9, #fbb6ce);
    border-radius: 10px;
    color: #2d3748;
    text-align: center;
    font-size: 1.1em;
    padding: 12px 6px;
    font-weight: 700;
    margin-bottom: 5px;
}
.gem-missing {
    background-color: rgba(255,255,255,0.7);
    border-radius: 10px;
    color: #718096;
    text-align: center;
    font-size: 1.1em;
    padding: 12px 6px;
    font-weight: 700;
    margin-bottom: 5px;
    border: 1px solid rgba(127, 127, 127, 0.12);
}
/* hide toolbar and footer */
[data-testid="stToolbar"] {
    visibility: hidden !important;
}
footer {
    visibility: hidden !important;
}

"""
st.markdown(f"<style>{custom_css}</style>", unsafe_allow_html=True)

# --- game state ---

GAME_LOG_FILE = "game_log.csv"

def initialize_session():
    if 'page' not in st.session_state: st.session_state.page = "home"
    if 'player_name' not in st.session_state: st.session_state.player_name = ""
    if 'game_log' not in st.session_state:
        if os.path.exists(GAME_LOG_FILE): st.session_state.game_log = pd.read_csv(GAME_LOG_FILE)
        else: st.session_state.game_log = pd.DataFrame(columns=["Player", "Mode", "Attempts"])

def reset_game_state():
    st.session_state.collected_items = set()
    st.session_state.attempts = 0
    st.session_state.last_5_items = []
    st.session_state.is_new = False
    st.session_state.logged = False
    st.session_state.n_items = 20
    st.session_state.rare_gem = random.randint(1, st.session_state.n_items)
    st.session_state.joker_gem = random.randint(1, st.session_state.n_items)
    st.session_state.has_joker = False
    st.session_state.used_joker = False

def use_joker_bonus():
    if st.session_state.has_joker and not st.session_state.used_joker:
        uncollected = set(range(1, st.session_state.n_items + 1)) - st.session_state.collected_items
        if uncollected:
            new_gem = random.choice(list(uncollected))
            st.session_state.collected_items.add(new_gem)
            st.session_state.used_joker = True
            st.session_state.last_5_items.insert(0, f"🃏 #{new_gem} (Joker!)")
            st.session_state.last_5_items = st.session_state.last_5_items[:5]
            st.session_state.is_new = True

def log_game_result():
    new_entry = pd.DataFrame([{"Player": st.session_state.player_name, "Mode": st.session_state.game_mode, "Attempts": st.session_state.attempts}])
    st.session_state.game_log = pd.concat([st.session_state.game_log, new_entry], ignore_index=True)
    st.session_state.game_log.to_csv(GAME_LOG_FILE, index=False)
    st.session_state.logged = True

def calculate_theoretical_ev(n):
    if n <= 0: return 0
    return n * sum(1/i for i in range(1, n + 1))

# --- monte carlo simulation ---
@st.cache_data
def run_simulation(designs, n_items, n_trials, price, bonus_chance, rare_prob):
    all_results = []
    for design in designs:
        for i in range(n_trials):
            collected, attempts = set(), 0
            if design == "Equal Chance":
                while len(collected) < n_items:
                    collected.add(random.randint(1, n_items)); attempts += 1
            elif design == "Rare Item":
                rare_item = random.randint(1, n_items)
                while len(collected) < n_items:
                    if random.random() < rare_prob: collected.add(rare_item)
                    else: collected.add(random.choice([i for i in range(1, n_items + 1) if i != rare_item]))
                    attempts += 1
            elif design == "Surprise Bonus":
                while len(collected) < n_items:
                    collected.add(random.randint(1, n_items))
                    if random.random() < bonus_chance: collected.add(random.randint(1, n_items))
                    attempts += 1
            all_results.append({"design": design, "attempts": attempts})
    df = pd.DataFrame(all_results)
    df['total_cost'] = df['attempts'] * price
    return df

# --- pages ---

def render_home_page():
    st.header("Welcome, Collector!")
    name = st.text_input("Enter your name to begin:", key="name_input")
    if st.button("Start Quest"):
        if name.strip():
            st.session_state.player_name = name.strip()
            st.session_state.page = "mode_select"
            st.rerun()
        else:
            st.warning("A name is required to start your legacy!")

def render_mode_select_page():
    st.header(f"Welcome, {st.session_state.player_name}! Choose your challenge.")
    mode = st.radio("Select a reward design:",
                    ["🏪 Equal Chance Mart", "🏆 Rare Item Trove", "🎁 Surprise Bonus Shop (with Joker!)"],
                    captions=["Every item has an equal probability.",
                              "One item is significantly harder to find.",
                              "Chance for bonus items & a special Joker Gem!"],
                    horizontal=True)
    if st.button("Begin Collecting!"):
        clean_mode = " ".join(mode.split(" ")[1:])
        st.session_state.game_mode = clean_mode
        reset_game_state()
        st.session_state.page = "game"
        st.rerun()

def render_game_page():
    st.header(f"Quest: {st.session_state.game_mode}")
    if "Rare Item" in st.session_state.game_mode:
        st.info(f"🔮 The Mystical Rare Gem for this round is: #{st.session_state.rare_gem}. Good luck finding it!")
    if "Surprise Bonus" in st.session_state.game_mode and st.session_state.has_joker and not st.session_state.used_joker:
        st.success("⭐ You found the Joker Gem! Use the 'Joker Bonus' button below to claim a guaranteed new item!")
    if len(st.session_state.collected_items) >= st.session_state.n_items:
        st.balloons()
        st.success(f"🎉 Fantastic! You've collected all {st.session_state.n_items} gems!")
        st.metric("Total Attempts", st.session_state.attempts)
        if not st.session_state.logged:
            if st.button("Log My Result", type="primary"):
                log_game_result(); st.info("Your achievement has been recorded!"); st.rerun()
        c1, c2 = st.columns(2)
        c1.button("Play Again", on_click=lambda: st.session_state.update(page="mode_select"))
        c2.button("Change Player (Home)", on_click=lambda: st.session_state.update(page="home"))
        return

    c1, c2 = st.columns([1, 2.5], gap="large")
    with c1:
        if st.button("🎁 Get a New Gem!", type="primary"):
            st.session_state.attempts += 1
            items_before = len(st.session_state.collected_items)
            if "Equal Chance" in st.session_state.game_mode: new_item = random.randint(1, st.session_state.n_items)
            elif "Rare Item" in st.session_state.game_mode:
                if random.random() < 0.02: new_item = st.session_state.rare_gem
                else: new_item = random.choice([i for i in range(1, st.session_state.n_items + 1) if i != st.session_state.rare_gem])
            else:
                new_item = random.randint(1, st.session_state.n_items)
                if random.random() < 0.1: st.session_state.collected_items.add(random.randint(1, st.session_state.n_items))
            st.session_state.collected_items.add(new_item)
            is_new_now = len(st.session_state.collected_items) > items_before
            st.session_state.last_5_items.insert(0, f"#{new_item}{' (New!)' if is_new_now else ''}")
            st.session_state.last_5_items = st.session_state.last_5_items[:5]
            st.session_state.is_new = is_new_now
            if "Surprise Bonus" in st.session_state.game_mode and new_item == st.session_state.joker_gem and not st.session_state.has_joker:
                st.session_state.has_joker = True
            st.rerun()
        st.metric("Attempts", st.session_state.attempts)
        st.progress(len(st.session_state.collected_items) / st.session_state.n_items)
        st.write(f"{len(st.session_state.collected_items)} / {st.session_state.n_items} unique gems found")
        if "Surprise Bonus" in st.session_state.game_mode and st.session_state.has_joker:
            st.button("🃏 Use Joker Bonus!", on_click=use_joker_bonus, disabled=st.session_state.used_joker, help="Claim a guaranteed new gem!")
        if st.session_state.last_5_items:
            st.subheader("Recent Finds:")
            for item in st.session_state.last_5_items:
                if "New!" in item: st.success(f"✨ {item}")
                elif "Joker!" in item: st.success(f"🃏 {item}")
                else: st.warning(f"💢 {item} (Duplicate)")
    with c2:
        cols = st.columns(10)
        for i in range(1, st.session_state.n_items + 1):
            with cols[(i - 1) % 10]:
                if i in st.session_state.collected_items: st.markdown(f"<div class='gem-collected'>💎<br>{i}</div>", unsafe_allow_html=True)
                else: st.markdown(f"<div class='gem-missing'>❔<br>{i}</div>", unsafe_allow_html=True)

def render_simulation_page():
    st.header("📊 Simulation Dashboard")
    st.markdown("Analyze the financial and psychological impact of different reward designs.")
    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1:
            st.subheader("Core Parameters")
            n_items = st.slider("Number of unique items", 10, 100, 20)
            n_trials = st.slider("Simulation trials per design", 100, 5000, 1000)
            price = st.number_input("Price per attempt (₹)", min_value=1, value=20)
        with c2:
            st.subheader("Design-Specific Rules")
            bonus_chance = st.slider("Bonus Chance % (Surprise Bonus)", 1, 50, 10) / 100.0
            rare_prob = st.slider("Rare Item Probability % (Rare Item)", 1, 20, 2) / 100.0
        with c3:
            st.subheader("Run Analysis")
            st.info("Click below to run the full simulation based on your parameters.")
            if st.button("🚀 Launch Simulation", type="primary", use_container_width=True):
                st.session_state.sim_results = run_simulation(["Equal Chance", "Rare Item", "Surprise Bonus"], n_items, n_trials, price, bonus_chance, rare_prob)
                st.session_state.n_items_sim = n_items

    if 'sim_results' in st.session_state:
        df = st.session_state.sim_results
        st.markdown("---")
        st.subheader("Simulation Results")
        
        pastel_colors = px.colors.qualitative.Pastel
        
        tab1, tab2, tab3 = st.tabs(["📈 Cost & Effort Analysis", "🎲 Risk & Distribution", "💡 Key Takeaways"])

        with tab1:
            st.subheader("Average Cost to Complete a Collection")
            cost_summary = df.groupby('design')['total_cost'].mean().reset_index()
            fig_cost = px.bar(cost_summary, x='design', y='total_cost', color='design',
                              labels={'total_cost': 'Average Total Cost (₹)', 'design': 'Reward Design'},
                              text_auto='.2s', color_discrete_sequence=pastel_colors)
            st.plotly_chart(fig_cost, use_container_width=True)
            st.markdown("""
            *Analysis Point:* This chart reveals the expected financial commitment for the average consumer. The 'Rare Item' design is clearly the most expensive to complete, suggesting a strategy focused on high-value customers. The 'Surprise Bonus' model is the most affordable, appealing to a broader audience.
            """)

            st.subheader("Simulation vs. Theory")
            simulated_means = df.groupby('design')['attempts'].mean().to_dict()
            theoretical_ev = calculate_theoretical_ev(st.session_state.n_items_sim)
            plot_data = {'Design': [], 'Value Type': [], 'Attempts': []}
            for design, mean in simulated_means.items():
                plot_data['Design'].append(design); plot_data['Value Type'].append('Simulated Mean'); plot_data['Attempts'].append(mean)
            plot_data['Design'].append('Equal Chance'); plot_data['Value Type'].append('Theoretical EV'); plot_data['Attempts'].append(theoretical_ev)
            plot_df = pd.DataFrame(plot_data)
            fig_ev = px.bar(plot_df, x='Design', y='Attempts', color='Value Type',
                            barmode='group', title="Model Validation: Simulated Mean vs. Theoretical EV",
                            labels={'Attempts': 'Number of Attempts'},
                            color_discrete_map={'Simulated Mean': '#5A67D8', 'Theoretical EV': '#FFBF00'})
            st.plotly_chart(fig_ev, use_container_width=True)
            st.info("This chart validates our simulation. For 'Equal Chance,' the simulated result closely matches the mathematical theory, confirming our model's accuracy.")

        with tab2:
            st.subheader("Understanding the Risk: Best vs. Worst Case Scenarios")
            fig_box = px.box(df, x='design', y='attempts', color='design',
                             title="Distribution of Attempts for Each Design",
                             color_discrete_sequence=pastel_colors)
            st.plotly_chart(fig_box, use_container_width=True)
            st.markdown("""
            *Analysis Point:* The Box Plot shows player experience variance. The long 'whisker' for the 'Rare Item' design highlights a high-risk scenario where many players will need significantly more attempts than the average, leading to frustration. The compact box for the 'Surprise Bonus' indicates a more predictable and fair experience.
            """)
            
            st.subheader("Statistical Deep Dive: Where Do Most Results Fall?")
            fig_violin = px.violin(df, x='design', y='attempts', color='design',
                                   title="Probability Density of Attempts",
                                   box=True, points="all",
                                   color_discrete_sequence=pastel_colors)
            st.plotly_chart(fig_violin, use_container_width=True)
            st.markdown("""
            *Analysis Point:* The Violin Plot reveals the probability of outcomes. The wide shape for 'Surprise Bonus' shows most players finish near the average. The tall, thin shape for 'Rare Item' shows that while some get lucky, the outcomes are stretched across a huge range, with a long 'tail' representing very unlucky players.
            """)

        with tab3:
            st.subheader("Actionable Insights & Business Strategy")
            st.markdown("""
            Based on the simulation, each reward design serves a different business goal:

            - *💡 Equal Chance:*
              - *Best For:* Building trust and fairness.
              - *Strategy:* Use for brand promotions where customer goodwill is the primary goal. It's predictable and easy to explain.

            - *💎 Rare Item:*
              - *Best For:* Maximizing revenue from dedicated collectors and creating hype.
              - *Strategy:* Use for limited-edition campaigns with a high-value "chase" item. This model encourages a secondary market (trading) but risks frustrating the majority of players.

            - *🎁 Surprise Bonus:*
              - *Best For:* Long-term engagement and customer retention.
              - *Strategy:* Implement in loyalty programs. The bonus mechanic acts as a 'frustration safety net,' preventing players from quitting after a streak of bad luck and encouraging continued participation.
            """)

def render_log_page():
    st.header("📜 Player Game Log")
    if not st.session_state.game_log.empty:
        st.dataframe(st.session_state.game_log, use_container_width=True)
        st.download_button(label="📥 Download Log as CSV",
                           data=st.session_state.game_log.to_csv(index=False).encode('utf-8'),
                           file_name='collector_game_log.csv', mime='text/csv')
    else:
        st.info("No games have been logged yet. Play a game to see your results here!")

# --- main ---
initialize_session()
st.title("Collector's Dilemma")
selected_page = st.radio("Navigation", ["Game", "Simulation", "Game Log"], horizontal=True, label_visibility="collapsed")

if selected_page == "Game":
    if st.session_state.page == "home": render_home_page()
    elif st.session_state.page == "mode_select": render_mode_select_page()
    elif st.session_state.page == "game": render_game_page()
elif selected_page == "Simulation": render_simulation_page()
elif selected_page == "Game Log": render_log_page()