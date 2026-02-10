"""
STREAMLIT WEB APP - Mark Minervini Stock Screener
Beautiful web interface for the Enhanced Minervini Screener
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="Minervini Stock Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stAlert {
        padding: 1rem;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Import the screener class
class MinerviniScreenerEnhanced:
    
    def __init__(self, symbol, account_balance=100000):
        self.symbol = symbol.upper()
        self.account_balance = account_balance
        self.stock = None
        self.hist = None
        self.current_price = None
        
    def fetch_data(self, period='2y'):
        try:
            self.stock = yf.Ticker(self.symbol)
            self.hist = self.stock.history(period=period)
            
            if self.hist.empty:
                return False
                
            self.current_price = self.hist['Close'].iloc[-1]
            return True
        except Exception as e:
            st.error(f"Error fetching data for {self.symbol}: {str(e)}")
            return False
    
    def calculate_moving_averages(self):
        self.hist['SMA_10'] = self.hist['Close'].rolling(window=10).mean()
        self.hist['SMA_20'] = self.hist['Close'].rolling(window=20).mean()
        self.hist['SMA_50'] = self.hist['Close'].rolling(window=50).mean()
        self.hist['SMA_150'] = self.hist['Close'].rolling(window=150).mean()
        self.hist['SMA_200'] = self.hist['Close'].rolling(window=200).mean()
    
    def analyze_volume(self):
        try:
            avg_volume = self.hist['Volume'].tail(50).mean()
            current_volume = self.hist['Volume'].iloc[-1]
            vol_ratio = current_volume / avg_volume
            
            if vol_ratio >= 2.0:
                signal = "STRONG ACCUMULATION"
            elif vol_ratio >= 1.5:
                signal = "INSTITUTIONAL BUYING"
            elif vol_ratio >= 1.0:
                signal = "Above Average"
            else:
                signal = "Below Average"
            
            return vol_ratio, signal, avg_volume
        except:
            return 1.0, "Unable to calculate", 0
    
    def calculate_relative_strength(self):
        try:
            spy = yf.Ticker('SPY').history(period='1y')
            
            if len(self.hist) >= 126 and len(spy) >= 126:
                stock_return = (self.hist['Close'].iloc[-1] / self.hist['Close'].iloc[-126] - 1) * 100
                spy_return = (spy['Close'].iloc[-1] / spy['Close'].iloc[-126] - 1) * 100
                rs_advantage = stock_return - spy_return
            else:
                stock_return = (self.hist['Close'].iloc[-1] / self.hist['Close'].iloc[0] - 1) * 100
                spy_return = (spy['Close'].iloc[-1] / spy['Close'].iloc[0] - 1) * 100
                rs_advantage = stock_return - spy_return
            
            if rs_advantage >= 20:
                rating = "EXCEPTIONAL"
            elif rs_advantage >= 10:
                rating = "STRONG"
            elif rs_advantage >= 0:
                rating = "Outperforming"
            else:
                rating = "Underperforming"
            
            return rs_advantage, stock_return, spy_return, rating
        except:
            return 0, 0, 0, "Unable to calculate"
        
    def minervini_trend_template(self):
        criteria = {}
        
        try:
            current = self.hist.iloc[-1]
            
            criteria['price_above_150sma'] = current['Close'] > current['SMA_150']
            criteria['price_above_200sma'] = current['Close'] > current['SMA_200']
            criteria['150sma_above_200sma'] = current['SMA_150'] > current['SMA_200']
            
            sma_200_now = current['SMA_200']
            sma_200_month_ago = self.hist['SMA_200'].iloc[-22] if len(self.hist) >= 22 else None
            criteria['200sma_trending_up'] = sma_200_now > sma_200_month_ago if sma_200_month_ago else False
            
            criteria['50sma_above_150sma'] = current['SMA_50'] > current['SMA_150']
            criteria['50sma_above_200sma'] = current['SMA_50'] > current['SMA_200']
            criteria['price_above_50sma'] = current['Close'] > current['SMA_50']
            
            low_52week = self.hist['Low'].iloc[-252:].min() if len(self.hist) >= 252 else self.hist['Low'].min()
            criteria['price_above_52w_low'] = (current['Close'] / low_52week - 1) >= 0.30
            
            high_52week = self.hist['High'].iloc[-252:].max() if len(self.hist) >= 252 else self.hist['High'].max()
            distance_from_high = (high_52week - current['Close']) / high_52week
            criteria['price_near_52w_high'] = distance_from_high <= 0.25
            
            rs_advantage, _, _, _ = self.calculate_relative_strength()
            criteria['outperforming_market'] = rs_advantage > 0
            
            valid_criteria = {k: v for k, v in criteria.items() if v is not None}
            passed = sum(valid_criteria.values())
            total = len(valid_criteria)
            
            return passed >= 7, criteria, passed, total
        except Exception as e:
            return False, criteria, 0, 8
    
    def identify_stage(self):
        try:
            current = self.hist.iloc[-1]
            
            if pd.isna(current['SMA_150']):
                return 0, "Insufficient data"
            
            sma_150_rising = current['SMA_150'] > self.hist['SMA_150'].iloc[-10]
            price_above_150 = current['Close'] > current['SMA_150']
            
            recent_highs = self.hist['High'].iloc[-60:]
            making_higher_highs = recent_highs.iloc[-1] == recent_highs.max()
            
            if price_above_150 and sma_150_rising and making_higher_highs:
                return 2, "Stage 2: Advancing (IDEAL)"
            elif price_above_150 and sma_150_rising:
                return 2, "Stage 2: Advancing"
            elif price_above_150:
                return 1, "Stage 1: Basing"
            else:
                return 4, "Stage 4: Declining"
        except:
            return 0, "Error"
    
    def detect_vcp_pattern(self):
        try:
            if len(self.hist) < 50:
                return False, "Insufficient data"
            
            recent = self.hist.tail(50).copy()
            recent['Range'] = recent['High'] - recent['Low']
            recent['Volatility'] = recent['Range'].rolling(10).mean()
            
            vol_now = recent['Volatility'].iloc[-1]
            vol_20 = recent['Volatility'].iloc[-20] if len(recent) >= 20 else vol_now
            vol_40 = recent['Volatility'].iloc[-40] if len(recent) >= 40 else vol_now
            
            contracting = vol_now < vol_20 < vol_40
            tight = all(recent['Range'].iloc[-3:] / recent['Close'].iloc[-3:] < 0.015)
            
            if contracting and tight:
                return True, "VCP detected: Tight action"
            elif contracting:
                return True, "VCP forming"
            else:
                return False, "No VCP"
        except:
            return False, "Error"
    
    def detect_cup_with_handle(self):
        try:
            if len(self.hist) < 60:
                return False, None, "Insufficient data"
            
            lookback = min(120, len(self.hist))
            recent = self.hist.tail(lookback).copy()
            
            cup_high_idx = recent['High'].iloc[:-20].idxmax()
            cup_high = recent.loc[cup_high_idx, 'High']
            
            cup_low_idx = recent.loc[cup_high_idx:]['Low'].iloc[:40].idxmin() if len(recent.loc[cup_high_idx:]) >= 40 else recent['Low'].idxmin()
            cup_low = recent.loc[cup_low_idx, 'Low']
            
            cup_depth = (cup_high - cup_low) / cup_high
            
            if not (0.10 <= cup_depth <= 0.35):
                return False, None, "No valid cup"
            
            handle_data = recent.tail(15)
            handle_high = handle_data['High'].max()
            handle_low = handle_data['Low'].min()
            handle_depth = (handle_high - handle_low) / handle_high
            
            pivot = handle_high
            
            if 0.05 <= handle_depth <= 0.15 and handle_high >= cup_high * 0.95:
                return True, pivot, "Cup-with-Handle detected"
            else:
                return False, None, "Cup present, handle not ideal"
        except:
            return False, None, "Error"
    
    def detect_flat_base(self):
        try:
            if len(self.hist) < 25:
                return False, None, "Insufficient data"
            
            lookback = min(50, len(self.hist))
            recent = self.hist.tail(lookback).copy()
            
            high = recent['High'].max()
            low = recent['Low'].min()
            depth = (high - low) / high
            
            if depth < 0.15 and lookback >= 25:
                pivot = high
                current = recent['Close'].iloc[-1]
                distance = (current - pivot) / pivot * 100
                
                if distance >= -5:
                    return True, pivot, f"Flat Base detected"
            
            return False, None, "No flat base"
        except:
            return False, None, "Error"
    
    def calculate_buy_point_and_stops(self):
        results = {
            'buy_point': None,
            'current_price': self.current_price,
            'stop_loss': None,
            'profit_target_20pct': None,
            'profit_target_2to1': None,
            'profit_target_3to1': None,
            'pattern': None,
            'status': None
        }
        
        cup_detected, cup_pivot, cup_msg = self.detect_cup_with_handle()
        flat_detected, flat_pivot, flat_msg = self.detect_flat_base()
        vcp_detected, vcp_msg = self.detect_vcp_pattern()
        
        if cup_detected:
            pivot = cup_pivot
            pattern_name = "Cup-with-Handle"
        elif flat_detected:
            pivot = flat_pivot
            pattern_name = "Flat Base"
        elif vcp_detected:
            pivot = self.hist['High'].iloc[-10:].max()
            pattern_name = "VCP"
        else:
            pivot = self.hist['High'].iloc[-20:].max()
            pattern_name = "Recent Swing High"
        
        results['buy_point'] = pivot
        results['pattern'] = pattern_name
        
        recent_low = self.hist['Low'].iloc[-10:].min()
        technical_stop = recent_low * 0.99
        percentage_stop = pivot * 0.93
        
        results['stop_loss'] = max(technical_stop, percentage_stop)
        
        risk_per_share = pivot - results['stop_loss']
        
        results['profit_target_20pct'] = pivot * 1.20
        results['profit_target_2to1'] = pivot + (risk_per_share * 2)
        results['profit_target_3to1'] = pivot + (risk_per_share * 3)
        
        distance_from_pivot = (self.current_price - pivot) / pivot * 100
        
        if -2 <= distance_from_pivot <= 0:
            results['status'] = "AT BUY POINT"
        elif 0 < distance_from_pivot <= 5:
            results['status'] = "BREAKING OUT"
        elif distance_from_pivot > 5:
            results['status'] = "EXTENDED"
        else:
            results['status'] = f"BELOW PIVOT"
        
        results['distance_from_pivot'] = distance_from_pivot
        results['risk_per_share'] = risk_per_share
        
        return results
    
    def calculate_position_sizing(self, buy_point, stop_loss):
        risk_per_share = buy_point - stop_loss
        risk_budget = self.account_balance * 0.01
        max_shares = int(risk_budget / risk_per_share) if risk_per_share > 0 else 0
        total_investment = max_shares * buy_point
        portfolio_allocation_pct = (total_investment / self.account_balance) * 100
        
        return {
            'max_shares': max_shares,
            'pilot_quarter': int(max_shares / 4),
            'pilot_half': int(max_shares / 2),
            'pilot_three_quarter': int(max_shares * 3 / 4),
            'total_investment': total_investment,
            'portfolio_allocation_pct': portfolio_allocation_pct,
            'risk_budget': risk_budget
        }
    
    def grade_setup(self, trend_passed, trend_score, stage, pattern):
        score = 0
        score += (trend_score / 8) * 40
        
        if stage == 2 and "IDEAL" in str(stage):
            score += 30
        elif stage == 2:
            score += 25
        elif stage == 1:
            score += 15
        
        if pattern == "Cup-with-Handle":
            score += 30
        elif pattern == "Flat Base":
            score += 25
        elif pattern == "VCP":
            score += 28
        else:
            score += 10
        
        if score >= 90:
            return "A+", score
        elif score >= 85:
            return "A", score
        elif score >= 75:
            return "B+", score
        elif score >= 65:
            return "B", score
        elif score >= 50:
            return "C+", score
        else:
            return "C", score
    
    def analyze(self):
        if not self.fetch_data():
            return None
        
        self.calculate_moving_averages()
        
        vol_ratio, vol_signal, avg_vol = self.analyze_volume()
        rs_advantage, stock_ret, spy_ret, rs_rating = self.calculate_relative_strength()
        trend_passed, criteria, trend_score, total_criteria = self.minervini_trend_template()
        stage, stage_desc = self.identify_stage()
        buy_analysis = self.calculate_buy_point_and_stops()
        position = self.calculate_position_sizing(buy_analysis['buy_point'], buy_analysis['stop_loss'])
        grade, score = self.grade_setup(trend_passed, trend_score, stage, buy_analysis['pattern'])
        
        verdict = 'BUY' if buy_analysis['status'] in ["AT BUY POINT", "BREAKING OUT"] and grade in ["A+", "A", "B+"] else 'WAIT'
        
        return {
            'symbol': self.symbol,
            'verdict': verdict,
            'grade': grade,
            'score': score,
            'current_price': buy_analysis['current_price'],
            'buy_point': buy_analysis['buy_point'],
            'stop_loss': buy_analysis['stop_loss'],
            'target_20pct': buy_analysis['profit_target_20pct'],
            'target_2to1': buy_analysis['profit_target_2to1'],
            'target_3to1': buy_analysis['profit_target_3to1'],
            'status': buy_analysis['status'],
            'pattern': buy_analysis['pattern'],
            'stage': stage_desc,
            'trend_score': f"{trend_score}/{total_criteria}",
            'trend_passed': trend_passed,
            'criteria': criteria,
            'volume_ratio': vol_ratio,
            'volume_signal': vol_signal,
            'rs_advantage': rs_advantage,
            'rs_rating': rs_rating,
            'stock_return': stock_ret,
            'spy_return': spy_ret,
            'max_shares': position['max_shares'],
            'pilot_quarter': position['pilot_quarter'],
            'pilot_half': position['pilot_half'],
            'total_investment': position['total_investment'],
            'portfolio_allocation': position['portfolio_allocation_pct'],
            'risk_budget': position['risk_budget'],
            'distance_from_pivot': buy_analysis['distance_from_pivot']
        }


# Main Streamlit App
def main():
    st.markdown('<h1 class="main-header">📈 Mark Minervini Stock Screener</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <p style='font-size: 1.2rem;'>
            Professional stock analysis based on <strong>SEPA</strong> methodology from 
            <em>"Trade Like a Stock Market Wizard"</em>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        account_balance = st.number_input(
            "Account Balance ($)",
            min_value=1000,
            max_value=10000000,
            value=100000,
            step=10000,
            help="Your total trading account size"
        )
        
        risk_pct = st.slider(
            "Risk per Trade (%)",
            min_value=0.5,
            max_value=3.0,
            value=1.0,
            step=0.5,
            help="Minervini recommends 1% max"
        )
        
        st.markdown("---")
        
        st.markdown("""
        ### 📚 Quick Guide
        
        **Setup Grades:**
        - **A+/A**: Buy-worthy setups
        - **B+**: Acceptable if volume confirms
        - **B/C**: Avoid or wait
        
        **Volume Signal:**
        - **2.0x+**: Strong accumulation
        - **1.5x+**: Institutional buying
        - **<1.0x**: Caution
        
        **Position Sizing:**
        - Start with 1/4 pilot
        - Add if setup proves itself
        """)
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["🔍 Single Stock", "📊 Batch Screener", "📖 Help"])
    
    with tab1:
        st.subheader("Analyze Individual Stock")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            symbol = st.text_input(
                "Stock Symbol",
                value="NVDA",
                help="Enter stock ticker (e.g., AAPL, TSLA, NVDA)"
            ).upper()
        
        with col2:
            analyze_btn = st.button("🚀 Analyze", type="primary", use_container_width=True)
        
        if analyze_btn and symbol:
            with st.spinner(f"Analyzing {symbol}... This may take a few seconds..."):
                screener = MinerviniScreenerEnhanced(symbol, account_balance)
                result = screener.analyze()
                
                if result:
                    # Verdict Banner
                    if result['verdict'] == 'BUY':
                        st.success(f"✅ **{result['verdict']}** - High quality setup at proper entry point!", icon="✅")
                    else:
                        st.warning(f"⏸️ **{result['verdict']}** - {result['status']}", icon="⏸️")
                    
                    # Key Metrics
                    st.markdown("### 📊 Key Metrics")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "Setup Grade",
                            result['grade'],
                            f"{result['score']:.0f}/100"
                        )
                    
                    with col2:
                        st.metric(
                            "Current Price",
                            f"${result['current_price']:.2f}",
                            f"{result['distance_from_pivot']:+.1f}% from pivot"
                        )
                    
                    with col3:
                        st.metric(
                            "Volume Signal",
                            result['volume_signal'],
                            f"{result['volume_ratio']:.2f}x avg"
                        )
                    
                    with col4:
                        st.metric(
                            "RS vs Market",
                            result['rs_rating'],
                            f"{result['rs_advantage']:+.1f}%"
                        )
                    
                    # Trading Plan
                    st.markdown("### 🎯 Trading Plan")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**📍 Entry & Risk**")
                        
                        entry_data = {
                            "Metric": ["Buy Point", "Stop Loss", "Risk/Share"],
                            "Value": [
                                f"${result['buy_point']:.2f}",
                                f"${result['stop_loss']:.2f}",
                                f"${result['buy_point'] - result['stop_loss']:.2f}"
                            ]
                        }
                        st.dataframe(pd.DataFrame(entry_data), hide_index=True, use_container_width=True)
                        
                        st.markdown("**💼 Position Sizing**")
                        position_data = {
                            "Position": ["1/4 Pilot", "1/2 Position", "Full Position"],
                            "Shares": [
                                f"{result['pilot_quarter']:,}",
                                f"{result['pilot_half']:,}",
                                f"{result['max_shares']:,}"
                            ],
                            "Investment": [
                                f"${result['pilot_quarter'] * result['buy_point']:,.0f}",
                                f"${result['pilot_half'] * result['buy_point']:,.0f}",
                                f"${result['total_investment']:,.0f}"
                            ]
                        }
                        st.dataframe(pd.DataFrame(position_data), hide_index=True, use_container_width=True)
                    
                    with col2:
                        st.markdown("**🎯 Profit Targets**")
                        
                        target_data = {
                            "Target": ["20% Fixed", "2:1 Reward", "3:1 Reward (Ideal)"],
                            "Price": [
                                f"${result['target_20pct']:.2f}",
                                f"${result['target_2to1']:.2f}",
                                f"${result['target_3to1']:.2f}"
                            ],
                            "Gain": [
                                f"+{((result['target_20pct']/result['buy_point']-1)*100):.1f}%",
                                f"+{((result['target_2to1']/result['buy_point']-1)*100):.1f}%",
                                f"+{((result['target_3to1']/result['buy_point']-1)*100):.1f}%"
                            ]
                        }
                        st.dataframe(pd.DataFrame(target_data), hide_index=True, use_container_width=True)
                        
                        risk_reward = (result['target_3to1'] - result['buy_point']) / (result['buy_point'] - result['stop_loss'])
                        st.info(f"**Risk/Reward Ratio:** 1:{risk_reward:.2f}")
                    
                    # Trend Template
                    st.markdown("### 📈 Trend Template Analysis")
                    
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        if result['trend_passed']:
                            st.success(f"✅ PASSED ({result['trend_score']})", icon="✅")
                        else:
                            st.error(f"❌ FAILED ({result['trend_score']})", icon="❌")
                        
                        st.info(f"**Stage:** {result['stage']}")
                        st.info(f"**Pattern:** {result['pattern']}")
                    
                    with col2:
                        criteria_df = pd.DataFrame([
                            {"Criteria": k.replace('_', ' ').title(), "Status": "✓" if v else "✗"}
                            for k, v in result['criteria'].items()
                        ])
                        st.dataframe(criteria_df, hide_index=True, use_container_width=True)
                    
                    # Action Plan
                    if result['verdict'] == 'BUY':
                        st.markdown("### 🚀 Suggested Action Plan")
                        
                        st.success(f"""
                        **Step 1:** Enter with **{result['pilot_quarter']:,} shares** at ${result['buy_point']:.2f} (1/4 pilot position)
                        
                        **Step 2:** Set stop loss at ${result['stop_loss']:.2f} immediately
                        
                        **Step 3:** If stock holds entry and volume confirms, add to **{result['pilot_half']:,} shares**
                        
                        **Step 4:** On breakout with strong volume, complete to **{result['max_shares']:,} shares**
                        
                        **Step 5:** Take 25-50% profit at ${result['target_2to1']:.2f} (2:1 reward)
                        
                        **Step 6:** Trail stop with 10-day MA for remaining shares, target ${result['target_3to1']:.2f}
                        """)
                    else:
                        st.info(f"""
                        **Status:** {result['status']}
                        
                        **Action:** Add to watchlist. Wait for price to move toward buy point at ${result['buy_point']:.2f}
                        
                        **Distance from entry:** {result['distance_from_pivot']:.1f}%
                        """)
    
    with tab2:
        st.subheader("Batch Stock Screener")
        
        watchlist_input = st.text_area(
            "Enter stock symbols (comma-separated)",
            value="AAPL, MSFT, NVDA, TSLA, META, GOOGL",
            help="Enter multiple symbols separated by commas"
        )
        
        batch_btn = st.button("🔍 Screen All", type="primary", use_container_width=True)
        
        if batch_btn and watchlist_input:
            symbols = [s.strip().upper() for s in watchlist_input.split(',') if s.strip()]
            
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, symbol in enumerate(symbols):
                status_text.text(f"Analyzing {symbol}... ({i+1}/{len(symbols)})")
                
                screener = MinerviniScreenerEnhanced(symbol, account_balance)
                result = screener.analyze()
                
                if result:
                    results.append(result)
                
                progress_bar.progress((i + 1) / len(symbols))
            
            status_text.text("Analysis complete!")
            
            if results:
                df = pd.DataFrame(results)
                df = df.sort_values('score', ascending=False)
                
                # Filter tabs
                buy_tab, watch_tab, all_tab = st.tabs(["✅ BUY Signals", "⏸️ Watch List", "📋 All Results"])
                
                with buy_tab:
                    buy_signals = df[df['verdict'] == 'BUY']
                    
                    if not buy_signals.empty:
                        st.success(f"Found {len(buy_signals)} BUY signal(s)!", icon="✅")
                        
                        display_cols = ['symbol', 'grade', 'score', 'current_price', 'buy_point', 
                                      'stop_loss', 'target_3to1', 'volume_signal', 'pilot_quarter', 'max_shares']
                        st.dataframe(
                            buy_signals[display_cols].style.background_gradient(subset=['score'], cmap='RdYlGn'),
                            hide_index=True,
                            use_container_width=True
                        )
                    else:
                        st.info("No BUY signals found. Check the Watch List for potential setups.")
                
                with watch_tab:
                    watch_list = df[df['verdict'] == 'WAIT'].sort_values('score', ascending=False)
                    
                    if not watch_list.empty:
                        st.info(f"Monitoring {len(watch_list)} stock(s)")
                        
                        display_cols = ['symbol', 'grade', 'current_price', 'buy_point', 'distance_from_pivot', 'status']
                        st.dataframe(watch_list[display_cols], hide_index=True, use_container_width=True)
                
                with all_tab:
                    display_cols = ['symbol', 'verdict', 'grade', 'score', 'current_price', 
                                  'buy_point', 'target_3to1', 'volume_ratio', 'rs_advantage']
                    st.dataframe(
                        df[display_cols].style.background_gradient(subset=['score'], cmap='RdYlGn'),
                        hide_index=True,
                        use_container_width=True
                    )
    
    with tab3:
        st.markdown("""
        ## 📖 How to Use This Screener
        
        ### Overview
        This screener implements Mark Minervini's **SEPA (Specific Entry Point Analysis)** methodology from 
        *"Trade Like a Stock Market Wizard"* and *"Momentum Masters"*.
        
        ### Key Features
        
        #### 1. **Trend Template (8 Criteria)**
        Checks if stock meets Minervini's strict uptrend requirements:
        - Price above key moving averages (50, 150, 200-day)
        - Moving averages properly aligned
        - Price near 52-week high
        - Price well above 52-week low
        - Outperforming the market
        
        #### 2. **Volume Analysis**
        - **2.0x+ = Strong Accumulation** (institutions loading up)
        - **1.5x+ = Institutional Buying** (smart money entering)
        - **<1.0x = Caution** (lack of conviction)
        
        #### 3. **Position Sizing (1% Risk Rule)**
        Automatically calculates exactly how many shares to buy based on:
        - Your account size
        - Entry price
        - Stop loss price
        - Maximum 1% risk per trade
        
        #### 4. **Pilot Position Strategy**
        - **1/4 Position**: Test entry, prove the setup
        - **1/2 Position**: Add if stock holds
        - **Full Position**: Complete on volume breakout
        
        #### 5. **Trailing Stops**
        - Entry: Keep initial stop
        - Breakeven (0-10%): Move stop to breakeven
        - Profit Protection (10-20%): Lock in 1.5:1 gain
        - Superperformance (20%+): Trail with 10-day MA
        
        ### Reading the Grades
        
        - **A+** (90-100): Exceptional setup - all criteria aligned
        - **A** (85-89): Excellent setup - minor imperfections
        - **B+** (75-84): Good setup - acceptable with volume confirmation
        - **B** (65-74): Fair setup - proceed with extra caution
        - **C and below**: Poor setup - avoid
        
        ### Trading Rules
        
        1. **Only buy A+, A, or B+ grades** in Stage 2
        2. **Wait for volume confirmation** (1.5x+ on breakout)
        3. **Always start with pilot position** (1/4 shares)
        4. **Set stop loss immediately** - no exceptions
        5. **Move to breakeven once up 5-10%** - protect capital
        6. **Take partial profits at 2:1** (25-50% of position)
        7. **Let A+ setups run to 3:1** - trail stops loosely
        
        ### Risk Management
        
        - Never risk more than 1% per trade
        - Use proper position sizing (provided by screener)
        - If stop is hit, EXIT immediately
        - Don't average down on losing positions
        
        ### Disclaimer
        
        This tool is for **educational purposes only**. It implements publicly available principles 
        from Mark Minervini's books but is not affiliated with or endorsed by him.
        
        - Always conduct your own research
        - Never risk more than you can afford to lose
        - Consult a financial advisor before investing
        - Past performance does not guarantee future results
        
        ### Support
        
        For questions or issues, please review:
        - Mark Minervini's books: "Trade Like a Stock Market Wizard"
        - His methodology: Stage Analysis, SEPA, VCP patterns
        - Risk management principles: 1% rule, position sizing
        """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>Built with Streamlit | Data from Yahoo Finance | Educational Purposes Only</p>
        <p style='font-style: italic;'>"Buy right, sit tight." - Mark Minervini</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
