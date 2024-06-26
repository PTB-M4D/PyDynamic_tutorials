import os
import sys

datasets_dir = os.path.dirname(os.path.abspath("")) + "/datasets"
if datasets_dir not in sys.path:
    sys.path.append(datasets_dir)

from download_data import download_tutorial_data
from helper_methods import *
from matplotlib.pyplot import *
from meas_data_preprocessing import DATA_SOURCE_REPO
from PyDynamic.uncertainty.interpolate import interp1d_unc


def read_calib_data(infos=None, meas_scenario=None, verbose=True, do_plot=True):
    """Pre-processing of the hydrophone calibration data
    :param infos: dict, containing scenario information
    :param meas_scenario: index of measurement scenario (used if infos is None)
    :param verbose: Boolean; if true write info to command line
    :param do_plot: Boolean, if true plot data
    :return: infos, hyd_data as dict
    """
    if infos is None:
        if meas_scenario is not None:
            infos = {"i": meas_scenario}
        else:
            infos = {"i": 1}
    infos, measurementfile, noisefile, hydfilename = get_file_info(
        infos
    )  # file names and such
    # Before reading the data check if data is present and if not download it.
    measurementfile = download_tutorial_data(
        url=DATA_SOURCE_REPO + measurementfile.replace(" ", "%20")
    )
    noisefile = download_tutorial_data(
        url=DATA_SOURCE_REPO + noisefile.replace(" ", "%20")
    )
    hydfilename = download_tutorial_data(
        url=DATA_SOURCE_REPO + hydfilename.replace(" ", "%20")
    )
    infos["measurementfile"] = measurementfile
    infos["noisefile"] = noisefile
    infos["hydfilename"] = hydfilename

    # Reading data files
    imax = None
    hydcal_data = np.loadtxt(hydfilename, skiprows=1, delimiter=",")
    hyd_data = {"name": hydfilename}
    hyd_data["frequency"] = hydcal_data[:imax, 0] * 1e6
    hyd_data["real"] = hydcal_data[:imax, 1]
    hyd_data["imag"] = hydcal_data[:imax, 2]
    hyd_data["varreal"] = hydcal_data[:imax, 3]
    hyd_data["varimag"] = hydcal_data[:imax, 4]
    hyd_data["cov"] = hydcal_data[:imax, 5]

    if do_plot:
        ## Plot hydrophone calibration data
        figure(4)
        plot(
            hyd_data["frequency"] / 1e6,
            np.sqrt(hyd_data["real"] ** 2 + hyd_data["imag"] ** 2),
        )
        xlabel("Frequency f / MHz")
        ylabel("Sensitivity M / V/Pa")
        title("Filename: {}".format(hyd_data["name"]))

        figure(5)
        plot(
            hyd_data["frequency"] / 1e6, np.arctan2(hyd_data["imag"], hyd_data["real"])
        )
        xlabel("Frequency f / MHz")
        ylabel(r"Phase $\varphi$ / rad")
        title("Filename: {}".format(hyd_data["name"]))

    return infos, hyd_data


def reduce_freq_range(hyd_data, fmin=1e6, fmax=1e8):
    """reduce hydrophone data to relevant freq range
    :param hyd_data: dict containing data
    :param fmin: smallest frequency in relevant range
    :param fmax: largest frequency in relevant range
    :return: hyd_data as dict
    """
    # select frequency range
    imin = findnearestmatch(hyd_data["frequency"], fmin)
    imax = findnearestmatch(hyd_data["frequency"], fmax)
    hyd_data["frequency"] = hyd_data["frequency"][imin : imax + 1]
    hyd_data["imag"] = hyd_data["imag"][imin : imax + 1]
    hyd_data["varimag"] = hyd_data["varimag"][imin : imax + 1]
    hyd_data["real"] = hyd_data["real"][imin : imax + 1]
    hyd_data["varreal"] = hyd_data["varreal"][imin : imax + 1]
    hyd_data["cov"] = hyd_data["cov"][imin : imax + 1]
    return hyd_data


def interpolate_hyd(hyd_data, f):
    # Interpolation and extrapolation of calibration data
    hyd_interpolated = {"frequency": f}
    N = len(f) // 2
    # interpolate real part in selected frequency range
    (
        hyd_interpolated["frequency"],
        hyd_interpolated["real"],
        hyd_interpolated["varreal"],
        Creal,
    ) = interp1d_unc(
        f[:N],
        hyd_data["frequency"],
        hyd_data["real"],
        hyd_data["varreal"],
        bounds_error=False,
        fill_value="extrapolate",
        fill_unc="extrapolate",
        returnC=True,
    )

    # interpolate imag part in selected frequency range
    hyd_interpolated["imag"] = np.zeros((N,))
    hyd_interpolated["varimag"] = np.zeros((N,))
    (
        hyd_interpolated["frequency"],
        hyd_interpolated["imag"],
        hyd_interpolated["varimag"],
        Cimag,
    ) = interp1d_unc(
        f[:N],
        hyd_data["frequency"],
        hyd_data["imag"],
        hyd_data["varimag"],
        bounds_error=False,
        fill_value="extrapolate",
        fill_unc="extrapolate",
        returnC=True,
    )
    # adjustment of end points
    hyd_interpolated["imag"][0] = 0  # Must be 0 by definition
    hyd_interpolated["imag"][-1] = 0
    hyd_interpolated["varimag"][0] = 0  # Must be 0 by definition
    hyd_interpolated["varimag"][-1] = 0

    ## Use pseudo-interpolation for the covariances between real and imaginary parts
    hyd_interpolated["cov"] = (Creal.dot(np.diag(hyd_data["cov"]))).dot(Cimag.T)
    return hyd_interpolated


if __name__ == "__main__":
    infos, hyd_data = read_calib_data(meas_scenario=13)
    hyd_data = reduce_freq_range(hyd_data)

    show()
