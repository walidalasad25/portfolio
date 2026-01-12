import matplotlib
matplotlib.use('QTAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter, AutoDateLocator
import datetime
from matplotlib.ticker import MaxNLocator, FuncFormatter
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import QTimer, Qt
from Infrastructure.variables import BG_COLOR, PRIMARY_COLOR, SECONDARY_COLOR, TEXT_COLOR, BORDER_COLOR

class GraphsWidget(QWidget):
    def __init__(self, data_recorder, pomodoro_session=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.recorder = data_recorder
        self.pomodoro_session = pomodoro_session

        self.setStyleSheet(f"background-color: {BG_COLOR};")
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Figure
        self.figure = Figure(figsize=(6, 9), dpi=100)
        self.figure.patch.set_facecolor(BG_COLOR)
        self.figure.subplots_adjust(hspace=0.7, top=0.92, bottom=0.12, left=0.15, right=0.92)
        
        # Subplots
        self.ax1 = self.figure.add_subplot(3, 1, 1) # Active Time
        self.ax2 = self.figure.add_subplot(3, 1, 2) # Words
        self.ax3 = self.figure.add_subplot(3, 1, 3) # Chars
        
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setStyleSheet("background-color: transparent;")
        layout.addWidget(self.canvas)
        
        # Styles
        self.lines = {}
        self._init_plots()
        
        # Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(1000)
        
    def _init_plots(self):
        text_color = TEXT_COLOR
        grid_color = BORDER_COLOR
        
        plot_configs = [
            (self.ax1, "active", "ACTIVE FOCUS", PRIMARY_COLOR),   # Orange
            (self.ax2, "words", "WORDS WRITTEN", SECONDARY_COLOR), # Green
            (self.ax3, "chars", "CHARACTERS", "#9C27B0")          # Purple
        ]
        
        def format_y_time(x, pos):
            seconds = int(x)
            if seconds < 60:
                return f"{seconds}s"
            elif seconds < 3600:
                m = seconds // 60
                return f"{m}m"
            else:
                h = seconds // 3600
                m = (seconds % 3600) // 60
                return f"{h}h {m}m" if m > 0 else f"{h}h"
        
        for ax, key, title, color in plot_configs:
            ax.set_facecolor(BG_COLOR)
            # Brighter titles
            ax.set_title(title, color="#777777", fontsize=9, fontweight='bold', pad=15)

            ax.tick_params(axis='x', colors='#555555', labelsize=8)
            ax.tick_params(axis='y', colors='#555555', labelsize=8)
            
            # Minimalist Spines
            for spine in ['top', 'right', 'left']:
                ax.spines[spine].set_visible(False)
            ax.spines['bottom'].set_edgecolor('#2a2a2a')
            ax.spines['bottom'].set_linewidth(1)
            
            # Subtle Horizontal Grid
            ax.grid(True, axis='y', color=BORDER_COLOR, linestyle='-', linewidth=0.5, alpha=0.05)
            ax.margins(y=0.2)

            # Reduce Y-axis tick density
            ax.yaxis.set_major_locator(MaxNLocator(nbins=5, prune='both'))

            if key == "active":
                ax.yaxis.set_major_formatter(FuncFormatter(format_y_time))

            line, = ax.plot([], [], color=color, linewidth=2, alpha=0.9, zorder=4)
            self.lines[key] = line
            
            # Use AutoDateLocator for x-axis
            ax.xaxis.set_major_locator(AutoDateLocator(minticks=2, maxticks=4))
            ax.xaxis.set_major_formatter(DateFormatter('%I:%M %p'))

    def update_plots(self):
        if not self.isVisible():
            return

        t, active, words, chars, nodes, intentions = self.recorder.get_data()
        if not t: return

        is_maximized = self.isMaximized()
        relevant_labels = nodes if is_maximized else intentions

        # 1. Determine X-Axis Bounds
        now_dt = datetime.datetime.now()
        from Core.Services.timer_engine import PomodoroPhase
        is_focus = self.pomodoro_session and self.pomodoro_session.is_running and self.pomodoro_session.phase == PomodoroPhase.FOCUS
        
        if is_maximized:
            today = now_dt.date()
            start_limit = datetime.datetime.combine(today, datetime.time.min)
            end_limit = datetime.datetime.combine(today, datetime.time.max)
            fmt = '%I %p'
        else:
            theoretical_start = now_dt - datetime.timedelta(minutes=25)
            start_limit, end_limit = theoretical_start, now_dt
            if is_focus and self.pomodoro_session.start_time:
                start_limit = datetime.datetime.fromtimestamp(self.pomodoro_session.start_time)
                end_limit = start_limit + datetime.timedelta(minutes=25)
            elif self.pomodoro_session and self.pomodoro_session.phase == PomodoroPhase.BREAK and self.pomodoro_session.last_focus_start:
                start_limit = datetime.datetime.fromtimestamp(self.pomodoro_session.last_focus_start)
                end_limit = start_limit + datetime.timedelta(minutes=25)
            fmt = '%I:%M %p'

        # Filter Data
        start_idx = 0
        s_ts = start_limit.timestamp()
        for i, ts in enumerate(t):
            if ts >= s_ts:
                start_idx = i
                break
        
        v_dates = [datetime.datetime.fromtimestamp(ts) for ts in t[start_idx:]]
        v_active = active[start_idx:]
        v_words = words[start_idx:]
        v_chars = chars[start_idx:]
        v_labels = relevant_labels[start_idx:]
        
        if not v_dates: return

        # Update Lines (Downsampled)
        skip = 1 if len(v_dates) < 400 else 2
        self.lines["active"].set_data(v_dates[::skip], v_active[::skip])
        self.lines["words"].set_data(v_dates[::skip], v_words[::skip])
        self.lines["chars"].set_data(v_dates[::skip], v_chars[::skip])
        
        current_data = [v_active, v_words, v_chars]
        configs = [(self.ax1, PRIMARY_COLOR), (self.ax2, SECONDARY_COLOR), (self.ax3, "#9C27B0")]
        
        # Titles
        titles = (["ACTIVE FOCUS", "WORDS WRITTEN", "CHARACTERS"] if is_maximized or not (self.pomodoro_session and self.pomodoro_session.phase == PomodoroPhase.BREAK) 
                  else ["LAST SESSION FOCUS", "LAST SESSION WORDS", "LAST SESSION CHARS"])
        
        # Subplot Spacing
        if is_maximized:
            self.figure.subplots_adjust(hspace=0.5, top=0.94, bottom=0.08, left=0.1, right=0.95)
        else:
            self.figure.subplots_adjust(hspace=0.7, top=0.92, bottom=0.1, left=0.15, right=0.92)

        for i, (ax, color) in enumerate(configs):
            v_vals = current_data[i]
            ax.set_title(titles[i], color='#AAAAAA', fontsize=8, fontweight='bold', pad=10)
            
            # Clear previous artifacts
            for coll in list(ax.collections): coll.remove()
            for text in list(ax.texts): text.remove()
            for l in list(ax.lines):
                if l not in self.lines.values(): l.remove()
            
            # Fill transparency
            ax.fill_between(v_dates[::skip], v_vals[::skip], color=color, alpha=0.06, zorder=2)
            
            # End Pulse
            ax.scatter(v_dates[-1], v_vals[-1], color=color, s=50, alpha=0.3, zorder=5)
            ax.scatter(v_dates[-1], v_vals[-1], color='#FFFFFF', s=6, alpha=0.8, zorder=7)
            
            # --- Vertical Markers & Labels ---
            last_label, last_drawn_x = None, None
            height_levels = [0.85, 0.65, 0.45, 0.25]
            stagger_idx = 0
            
            x_min_f, x_max_f = matplotlib.dates.date2num(start_limit), matplotlib.dates.date2num(end_limit)
            min_h_dist = (x_max_f - x_min_f) * (0.05 if not is_maximized else 0.04)
            left_safe_margin = (x_max_f - x_min_f) * 0.05 # 5% margin from left axis
            
            for j in range(len(v_labels)):
                item = v_labels[j]
                if item and item != last_label:
                    x_dt, x_num = v_dates[j], matplotlib.dates.date2num(v_dates[j])
                    
                    # Vertical Line (on all axes)
                    ax.axvline(x=x_dt, color='#ffffff', linestyle='-', linewidth=0.5, alpha=0.1, zorder=1)
                    
                    # Task Label (ONLY on top axis)
                    if i == 0 and (last_drawn_x is None or (x_num - last_drawn_x) > min_h_dist):
                         # Adjust position to avoid Y-axis overlap if too far left
                         draw_x_num = max(x_num, x_min_f + left_safe_margin)
                         draw_x_dt = matplotlib.dates.num2date(draw_x_num)

                         y_pos_rel = height_levels[stagger_idx % len(height_levels)]
                         
                         # Use Axes Transform for fixed vertical positioning
                         label_fs = 7
                         ax.text(draw_x_dt, y_pos_rel, f" {item} ", color="white", fontsize=label_fs, 
                                 fontweight='bold', va='center', ha='left', zorder=20,
                                 transform=ax.get_xaxis_transform(), # X: data, Y: axes [0,1]
                                 bbox=dict(facecolor='#1a1a1a', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.2'))
                         
                         last_drawn_x = x_num
                         stagger_idx += 1
                last_label = item

        # 4. Final Pruning
        formatter = DateFormatter(fmt)
        tick_fs = 8
        for ax in [self.ax1, self.ax2, self.ax3]:
            ax.set_xlim(start_limit, end_limit)
            ax.xaxis.set_major_formatter(formatter)
            ax.tick_params(axis='y', labelsize=tick_fs)
            for label in ax.get_xticklabels():
                label.set_rotation(0) 
                label.set_fontsize(tick_fs)
        
        # Scale Y Axis
        cur_active = v_active[-1]
        start_active = v_active[0] if v_active else 0
        if is_maximized:
             # Extended view shows the full day's cumulative "mountain" starting from 0
             self.ax1.set_ylim(bottom=0, top=max(3600, cur_active * 1.1))
        else:
             # Mini view starts exactly from the baseline value at the start of the window
             self.ax1.set_ylim(bottom=start_active, top=max(start_active + 1, cur_active + 2500))
        
        for ax, vals in [(self.ax2, v_words), (self.ax3, v_chars)]:
            cur_v = vals[-1]
            start_v = vals[0] if vals else 0
            if is_maximized:
                ax.set_ylim(bottom=0, top=max(100, cur_v * 1.15))
            else:
                ax.set_ylim(bottom=start_v, top=max(start_v + 1, cur_v + max(10, cur_v * 0.15)))



        self.canvas.draw_idle()


