from glob import glob
from hypnospy import Wearable
from hypnospy.data import ActiwatchSleepData
from hypnospy.analysis import SleepWakeAnalysis
from hypnospy.analysis import TimeSeriesProcessing
from hypnospy.analysis import PhysicalActivity
from hypnospy import Experiment


if __name__ == "__main__":

    # Configure an Experiment
    exp = Experiment()

    file_path = "./data/small_collection_hchs/*"

    # Iterates over a set of files in a directory.
    # Unfortunately, we have to do it manually with RawProcessing because we are modifying the annotations
    for file in glob(file_path):
        pp = ActiwatchSleepData(file, col_for_datetime="time", col_for_pid="pid")
        w = Wearable(pp)  # Creates a wearable from a pp object
        exp.add_wearable(w)

    tsp = TimeSeriesProcessing(exp)

    tsp.fill_no_activity(-0.0001)
    tsp.detect_non_wear(strategy="choi")

    tsp.check_consecutive_days(5)
    print("Valid days:", tsp.get_valid_days())
    print("Invalid days:", tsp.get_invalid_days())

    tsp.detect_sleep_boundaries(strategy="annotation", annotation_hour_to_start_search=18)
    tsp.invalidate_day_if_no_sleep()
    print("Valid days:", tsp.get_valid_days())

    tsp.check_valid_days(min_activity_threshold=0, max_non_wear_minutes_per_day=180)
    print("Valid days:", tsp.get_valid_days())
    print("Invalid days:", tsp.get_invalid_days())

    tsp.drop_invalid_days()

    # TODO: PA bouts? How to?
    pa = PhysicalActivity(exp, lpa=0, mvpa=399, vpa=1404)
    pa.generate_pa_columns()
    mvpa_bouts = pa.get_mvpas(length_in_minutes=1, decomposite_bouts=False)
    lpa_bouts = pa.get_lpas(length_in_minutes=1, decomposite_bouts=False)

    print("DONE")
    

