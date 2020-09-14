import matplotlib.pyplot as plt
import matplotlib.dates as dates
import pandas as pd
from datetime import datetime, timedelta, time
import calendar
import seaborn as sns

from hypnospy import Wearable
from hypnospy import Experiment


class Viewer(object):

    def __init__(self, input: {Wearable, Experiment}):

        if type(input) is Wearable:
            self.wearables = [input]
        elif type(input) is Experiment:
            self.wearables = input.get_all_wearables()

        sns.set_context("talk", font_scale=1.3, rc={"axes.linewidth": 2, 'image.cmap': 'plasma', })
        plt.rcParams['font.size'] = 18
        plt.rcParams['image.cmap'] = 'plasma'
        plt.rcParams['axes.linewidth'] = 2
        plt.rc('font', family='serif')

    @staticmethod
    def __get_details(alphas, colors, edgecolors, labels, part, index,
                      default_alpha=1.0, default_color="black", default_edgecolor=None, default_label="label"):
        alpha, color, edgecolor, label = default_alpha, default_color, default_edgecolor, default_label
        if alphas is not None and part in alphas:
            alpha = alphas[part]
            if isinstance(alpha, list):
                alpha = alpha[index]
        if colors is not None and part in colors:
            color = colors[part]
            if isinstance(color, list):
                color = color[index]
        if edgecolors is not None and part in edgecolors:
            edgecolor = edgecolors[part]
            if isinstance(edgecolor, list):
                edgecolor = edgecolor[index]
        if labels is not None and part in labels:
            label = labels[part]
            if isinstance(label, list):
                label = label[index]

        return alpha, color, edgecolor, label

    @staticmethod
    def get_day_label(df):

        s = ""
        startdate = df.index[0]
        enddate = df.index[-1]

        if startdate.day == enddate.day:
            s = "%d - %s\n %s" % (
            startdate.day, calendar.month_name[startdate.month][:3], calendar.day_name[startdate.dayofweek])

        else:
            if startdate.month == enddate.month:
                s = "%d/%d - %s\n %s/%s" % (
                    startdate.day, enddate.day, calendar.month_name[startdate.month][:3],
                    calendar.day_name[startdate.dayofweek][:3], calendar.day_name[enddate.dayofweek][:3])
            else:
                s = "%d - %s/%d - %s\n %s/%s" % (
                    startdate.day, calendar.month_name[startdate.month][:3], enddate.day,
                    calendar.month_name[enddate.month][:3],
                    calendar.day_name[startdate.dayofweek][:3], calendar.day_name[enddate.dayofweek][:3])

        return s

    def view_signals(self, signal_categories: list = ["activity", "hr", "pa_intensity", "sleep"],
                     other_signals: list = [], signal_as_area: list = [], resample_to: str = None,
                     sleep_cols: list = [], select_days: list = None, zoom: list = ["00:00:00", "23:59:59"],
                     alphas: dict = None, colors: dict = None, edgecolors: dict = None, labels: dict = None
                     ):
        # Many days, one day per panel
        for wearable in self.wearables:
            Viewer.view_signals_wearable(wearable, signal_categories, other_signals, signal_as_area, resample_to,
                                         sleep_cols, select_days, zoom, alphas, colors, edgecolors, labels)

    @staticmethod
    def view_signals_wearable(wearable: Wearable, signal_categories: list, other_signals: list, signal_as_area: list,
                              resample_to: str, sleep_cols: list, select_days: list, zoom: list,
                              alphas: dict = None, colors: dict = None, edgecolors: dict = None, labels: dict = None):

        # Convert zoom to datatime object:
        assert len(zoom) == 2
        zoom_start = datetime.strptime(zoom[0], '%H:%M:%S')
        zoom_end = datetime.strptime(zoom[1], '%H:%M:%S')

        cols = []

        for signal in signal_categories:
            if signal == "activity":
                cols.append(wearable.get_activity_col())

            elif signal == "hr":
                if wearable.get_hr_col():
                    cols.append(wearable.get_hr_col())
                else:
                    raise KeyError("HR is not available for PID %s" % wearable.get_pid())

            elif signal == "pa_intensity":
                if hasattr(wearable, 'pa_intensity_cols'):
                    for pa in wearable.pa_intensity_cols:
                        if pa in wearable.data.keys():
                            cols.append(pa)

            elif signal == "sleep":
                for sleep_col in sleep_cols:
                    if sleep_col not in wearable.data.keys():
                        raise ValueError("Could not find sleep_col (%s). Aborting." % sleep_col)
                    cols.append(sleep_col)

            elif signal == "diary" and wearable.diary_onset in wearable.data.keys() and \
                    wearable.diary_offset in wearable.data.keys():
                cols.append(wearable.diary_onset)
                cols.append(wearable.diary_offset)

            else:
                cols.append(signal)

        if len(cols) == 0:
            raise ValueError("Aborting: Empty list of signals to show.")

        cols.append(wearable.time_col)
        for col in set(other_signals + signal_as_area):
            cols.append(col)

        df_plot = wearable.data[cols].set_index(wearable.time_col)

        if resample_to is not None:
            df_plot = df_plot.resample(resample_to).mean()

        # Add column for experiment day. It will be resampled using the the mean
        cols.append(wearable.experiment_day_col)

        changed_experiment_hour = False
        if zoom_start.hour != wearable.hour_start_experiment:
            changed_experiment_hour = True
            saved_start_hour = wearable.hour_start_experiment
            wearable.change_start_hour_for_experiment_day(zoom_start.hour)

        if resample_to is not None:
            df_plot[wearable.experiment_day_col] = wearable.data[
                [wearable.time_col, wearable.experiment_day_col]].set_index(wearable.time_col).resample(resample_to).median()
        else:
            df_plot[wearable.experiment_day_col] = wearable.data[
                [wearable.time_col, wearable.experiment_day_col]].set_index(wearable.time_col)[wearable.experiment_day_col]

        if changed_experiment_hour:
            wearable.change_start_hour_for_experiment_day(saved_start_hour)

        # Daily version
        # dfs_per_day = [pd.DataFrame(group[1]) for group in df_plot.groupby(df_plot.index.day)]
        # Based on the experiment day gives us the correct chronological order of the days
        if select_days is not None:
            df_plot = df_plot[df_plot[wearable.experiment_day_col].isin(select_days)]
            if df_plot.empty:
                raise ValueError("Invalid day selection: no remaining data to show.")

        dfs_per_group = [pd.DataFrame(group[1]) for group in df_plot.groupby(wearable.experiment_day_col)]

        fig, ax1 = plt.subplots(len(dfs_per_group), 1, figsize=(14, 8))

        if len(dfs_per_group) == 1:
            ax1 = [ax1]

        for idx in range(len(dfs_per_group)):
            maxy = 2

            df_panel = dfs_per_group[idx]

            if "activity" in signal_categories:
                alpha, color, edgecolor, label = Viewer.__get_details(alphas, colors, edgecolors, labels, "activity",
                                                                      None, default_label="Activity")
                maxy = max(maxy, df_panel[wearable.get_activity_col()].max())
                ax1[idx].plot(df_panel.index, df_panel[wearable.get_activity_col()], label=label, linewidth=2,
                              color=color, alpha=alpha)

            if "pa_intensity" in signal_categories:
                ax1[idx].fill_between(df_panel.index, 0, maxy, where=df_panel['hyp_vpa'], facecolor='forestgreen',
                                      alpha=alpha,
                                      label='VPA', edgecolor='forestgreen')
                only_mvpa = (df_panel['hyp_mvpa']) & (~df_panel['hyp_vpa'])
                ax1[idx].fill_between(df_panel.index, 0, maxy, where=only_mvpa, facecolor='palegreen', alpha=alpha,
                                      label='MVPA', edgecolor='palegreen')
                only_lpa = (df_panel['hyp_lpa']) & (~df_panel['hyp_mvpa']) & (~df_panel['hyp_vpa'])
                ax1[idx].fill_between(df_panel.index, 0, maxy, where=only_lpa, facecolor='honeydew', alpha=alpha,
                                      label='LPA', edgecolor='honeydew')
                ax1[idx].fill_between(df_panel.index, 0, maxy, where=df_panel['hyp_sed'], facecolor='palegoldenrod',
                                      alpha=alpha,
                                      label='sedentary', edgecolor='palegoldenrod')

            if "sleep" in signal_categories:
                facecolors = ['royalblue', 'green', 'orange']
                endy = 0
                addition = (maxy / len(sleep_cols))
                for i, sleep_col in enumerate(sleep_cols):
                    starty = endy
                    endy = endy + addition
                    sleeping = df_panel[sleep_col]  # TODO: get a method instead of an attribute
                    ax1[idx].fill_between(df_panel.index, starty, endy, where=sleeping, facecolor=facecolors[i],
                                          alpha=0.7, label=sleep_col)

            if "diary" in signal_categories and wearable.diary_onset in df_panel.keys() and wearable.diary_offset in df_panel.keys():
                diary_event = df_panel[
                    (df_panel[wearable.diary_onset] == True) | (df_panel[wearable.diary_offset] == True)].index
                ax1[idx].vlines(x=diary_event, ymin=0, ymax=maxy, facecolor='black', alpha=alpha, label='Diary',
                                linestyles="dashed")

            for i, col in enumerate(other_signals):
                # colors = ["orange", "violet", "pink", "gray"] # Change to paramters
                ax1[idx].plot(df_panel.index, df_panel[col], label=col, linewidth=1, color=colors[i], alpha=alpha)

            endy = 0
            addition = 0 if len(signal_as_area) == 0 else (maxy / len(signal_as_area))
            for i, col in enumerate(signal_as_area):
                alpha, color, edgecolor, label = Viewer.__get_details(alphas, colors, edgecolors, labels, "area", i,
                                                                      default_label=col, default_color="blue")

                starty = endy
                endy = endy + addition

                ax1[idx].fill_between(df_panel.index, starty, endy, where=df_panel[col], facecolor=color,
                                      alpha=alpha, label=label)

            # configure time limits (y-axis) for plot.
            ax1[idx].tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=True, rotation=0)
            ax1[idx].set_facecolor('snow')

            # If the user has not specified a zoom...
            if zoom_start == time(0, 0, 0) and zoom_end == time(23, 59, 59):
                new_start_datetime = df_panel.index[0] - timedelta(
                    hours=(df_panel.index[0].hour - wearable.hour_start_experiment) % 24,
                    minutes=df_panel.index[0].minute, seconds=df_panel.index[0].second),
                new_end_datetime = df_panel.index[0] - timedelta(
                    hours=(df_panel.index[0].hour - wearable.hour_start_experiment) % 24,
                    minutes=df_panel.index[0].minute, seconds=df_panel.index[0].second) + timedelta(minutes=1439)

            else:
                new_start_date = df_panel.index[0].date()
                new_start_datetime = datetime(new_start_date.year, new_start_date.month, new_start_date.day,
                                              zoom_start.hour, zoom_start.minute, zoom_start.second)

                new_end_date = df_panel.index[-1].date()
                new_end_datetime = datetime(new_end_date.year, new_end_date.month, new_end_date.day, zoom_end.hour,
                                            zoom_end.minute, zoom_end.second)

                if new_end_datetime < new_start_datetime:
                    print("Changing it here")
                    new_end_datetime = datetime(new_end_date.year, new_end_date.month, new_end_date.day + 1,
                                                int(zoom_end.hour), int(zoom_end.minute), int(zoom_end.second))

            new_start_datetime = pd.to_datetime(new_start_datetime)
            new_end_datetime = pd.to_datetime(new_end_datetime)

            ax1[idx].set_xlim(new_start_datetime, new_end_datetime)

            y_label = Viewer.get_day_label(df_panel)
            ax1[idx].set_ylabel("%s" % y_label, rotation=0, horizontalalignment="right", verticalalignment="center")

            ax1[idx].set_xticks([])
            ax1[idx].set_yticks([])

            # create a twin of the axis that shares the x-axis
            if "hr" in signal_categories:
                alpha, color, edgecolor, label = Viewer.__get_details(alphas, colors, edgecolors, labels, "hr", None,
                                                                      default_label="HR", default_color="red")

                ax2 = ax1[idx].twinx()
                ax2.plot(df_panel.index, df_panel[wearable.get_hr_col()], label=label, color=color)
                ax2.set_ylim(df_panel[wearable.get_hr_col()].min() - 5, df_panel[wearable.get_hr_col()].max() + 5)
                ax2.set_xticks([])
                ax2.set_yticks([])

        ax1[0].set_title("PID = %s" % wearable.get_pid(), fontsize=16)
        ax1[-1].set_xlabel('Time')
        ax1[-1].xaxis.set_minor_locator(dates.HourLocator(interval=4))  # every 4 hours
        ax1[-1].xaxis.set_minor_formatter(dates.DateFormatter('%H:%M'))  # hours and minutes

        handles, labels = ax1[-1].get_legend_handles_labels()
        # handles2, labels2 = ax2.get_legend_handles_labels()
        # fig.legend(handles + handles2, labels + labels2, loc='lower center', ncol=4)
        # return fig
        # ax.figure.savefig('%s_signals.pdf' % (self.get_pid()))
        # fig.suptitle("%s" % self.get_pid(), fontsize=16)

        fig.legend(handles, labels, loc='lower center', ncol=len(cols), fontsize=14, shadow=True)
        fig.savefig('%s_signals.pdf' % (wearable.get_pid()), dpi=300, transparent=True, bbox_inches='tight')


    def view_signals_multipanel(self, wearable, signals: list,
                                signals_as_area: list,
                                select_day,
                                resample_to: str = None, zoom: list = ["00:00:00", "23:59:59"],
                                alphas: dict = None, colors: dict = None, edgecolors: dict = None, labels: dict = None,
                                ):

        # One single day -- multiple panels

        # Convert zoom to datatime object:
        assert len(zoom) == 2
        zoom_start = datetime.strptime(zoom[0], '%H:%M:%S')
        zoom_end = datetime.strptime(zoom[1], '%H:%M:%S')

        changed_experiment_hour = False
        if zoom_start.hour != wearable.hour_start_experiment:
            changed_experiment_hour = True
            saved_start_hour = wearable.hour_start_experiment
            wearable.change_start_hour_for_experiment_day(zoom_start.hour)

        df_plot = wearable.data[wearable.data[wearable.experiment_day_col] == select_day]

        if df_plot.empty:
            raise ValueError("Invalid day selection: no remaining data to show. Possible days are:",
                             df_plot[wearable.experiment_day_col].unique)

        cols = list(set(signals + signals_as_area)) + [wearable.time_col]
        df_plot = df_plot[cols].set_index(wearable.time_col)

        if resample_to is not None:
            df_plot = df_plot.resample(resample_to).mean()

        if changed_experiment_hour:
            wearable.change_start_hour_for_experiment_day(saved_start_hour)

        fig, ax = plt.subplots(len(signals) + len(signals_as_area), 1, figsize=(14, 8))

        if len(signals) == 1:
            ax = [ax]

        for idx in range(len(signals)):
            signal = signals[idx]
            maxy = 2

            alpha, color, edgecolor, label = self.__get_details(alphas, colors, edgecolors, labels, "signal", idx)

            maxy = max(maxy, df_plot[signal].max())
            ax[idx].plot(df_plot.index, df_plot[signal], label=label, linewidth=2, color=color, alpha=alpha)

            ax[idx].set_xticks([])
            ax[idx].set_yticks([])

            ax[idx].set_ylabel("%s" % label, rotation=0, horizontalalignment="right", verticalalignment="center")

        plot_idx = len(signals)

        for idx in range(len(signals_as_area)):
            signal = signals_as_area[idx]

            alpha, color, edgecolor, label = self.__get_details(alphas, colors, edgecolors, labels, "area", idx)

            idx = idx + plot_idx  # shifts idx to the point to the correct panel

            maxy = max(maxy, df_plot[signal].max())
            ax[idx].fill_between(df_plot.index, 0, maxy, where=df_plot[signal], facecolor=color, alpha=alpha,
                                 label=label, edgecolor=edgecolor)

            ax[idx].set_xticks([])
            ax[idx].set_yticks([])

            ax[idx].set_ylabel("%s" % label, rotation=0, horizontalalignment="right", verticalalignment="center")

        if zoom_start == time(0, 0, 0) and zoom_end == time(23, 59, 59):  # Default options, we use hour_start_experiment
            new_start_datetime = df_plot.index[0] - timedelta(
                hours=(df_plot.index[0].hour - wearable.hour_start_experiment) % 24,
                minutes=df_plot.index[0].minute, seconds=df_plot.index[0].second),
            new_end_datetime = df_plot.index[0] - timedelta(
                hours=(df_plot.index[0].hour - wearable.hour_start_experiment) % 24,
                minutes=df_plot.index[0].minute, seconds=df_plot.index[0].second) + timedelta(minutes=1439)

        else:
            new_start_date = df_plot.index[0].date()
            new_start_datetime = datetime(new_start_date.year, new_start_date.month, new_start_date.day,
                                          zoom_start.hour, zoom_start.minute, zoom_start.second)

            new_end_date = df_plot.index[-1].date()
            new_end_datetime = datetime(new_end_date.year, new_end_date.month, new_end_date.day, zoom_end.hour,
                                        zoom_end.minute, zoom_end.second)

            if new_end_datetime < new_start_datetime:
                print("Changing it here")
                new_end_datetime = datetime(new_end_date.year, new_end_date.month, new_end_date.day + 1,
                                            zoom_end.hour, zoom_end.minute, zoom_end.second)

        new_start_datetime = pd.to_datetime(new_start_datetime)
        new_end_datetime = pd.to_datetime(new_end_datetime)

        print(new_start_datetime, new_end_datetime)

        for idx in range(len(cols) - 1):
            ax[idx].set_xlim(new_start_datetime, new_end_datetime)

        ax[0].set_title("PID = %s" % wearable.get_pid(), fontsize=16)
        ax[-1].set_xlabel('Time')
        ax[-1].xaxis.set_minor_locator(dates.HourLocator(interval=4))  # every 4 hours
        ax[-1].xaxis.set_minor_formatter(dates.DateFormatter('%H:%M'))  # hours and minutes

        #fig.legend(loc='lower center', ncol=len(cols)-1, fontsize=14, shadow=True)
        fig.savefig('%s_signals.pdf' % (wearable.get_pid()), dpi=300, transparent=True, bbox_inches='tight')


    @staticmethod
    def plot_one_bland_altman(df_in, a, b, label1, label2, centralize_zero=True, plotname=None):
        sns.set_context("talk", font_scale=1.3, rc={"axes.linewidth": 2, 'image.cmap': 'plasma', })
        plt.rc('font', family='serif')

        df = df_in.copy()
        df["tst_" + a] = df["offset_" + a] - df["onset_" + a]
        df["tst_" + b] = df["offset_" + b] - df["onset_" + b]
        df["tst_average"] = (df["tst_" + a] + df["tst_" + b]) / 2.
        df["tst_diff"] = (df["tst_" + a] - df["tst_" + b])

        df["tst_average"] = df['tst_average'].dt.total_seconds() / 3600
        df["tst_diff"] = df['tst_diff'].dt.total_seconds() / 3600

        fig = plt.figure(figsize=(14, 8))
        plt.scatter(df['tst_average'], df['tst_diff'], color='blue')
        plt.axhline(df['tst_diff'].mean(), color='grey')
        plt.axhline(df['tst_diff'].mean() + df['tst_diff'].std(), linestyle='dashed', color='grey')
        plt.axhline(df['tst_diff'].mean() - df['tst_diff'].std(), linestyle='dashed', color='grey')
        plt.xlabel('TST average %s-%s (hours)' % (label1, label2))
        plt.ylabel('TST difference %s-%s (hours)' % (label1, label2))
        plt.title('Bland-Altman plot comparing %s and %s.' % (label1, label2))
        # plt.show(fig)

        if centralize_zero:
            ymax = df["tst_diff"].abs().max()
            plt.ylim(-ymax - 1, ymax + 1)

        if plotname:
            plt.savefig(plotname, dpi=200, bbox_inches='tight', facecolor='w', edgecolor='w', orientation='portrait',
                        transparent=True, pad_inches=0.01)

        return plt

    @staticmethod
    def plot_two_sleep_metrics(metric_a, metric_b, label_a, label_b, color="blue", alpha=1.0): #

        # Convert TST to dataframe
        dfa = pd.DataFrame(metric_a)

        # Convert SRI to dataframe
        dfb = pd.DataFrame(metric_b)

        # Drops NA and gets data that is in common
        merged = pd.merge(dfa, dfb, on=["pid", "expday"]).dropna()

        merged[label_a] = merged["value_x"]
        merged[label_b] = merged["value_y"]


        g = sns.jointplot(x=label_a, y=label_b, data=merged,
                          kind="reg", truncate=False, joint_kws = {'scatter_kws':dict(alpha=alpha)},
                          color=color, height=10)

        g.savefig('%s_by_%s.pdf' % (label_a, label_b), dpi=300, transparent=True, bbox_inches='tight')
