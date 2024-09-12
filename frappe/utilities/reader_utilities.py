import numpy as np
import pandas as pd
from scipy import optimize


def parse_tracks(tracks_path):
    # get the file extension
    file_extension = tracks_path.split(".")[-1]

    if file_extension == "npy":
        return read_minflux_file(tracks_path)


def read_minflux_file(minflux_tracks_path):

    minflux_npy = np.load(minflux_tracks_path)
    dt = find_minflux_timestep(minflux_npy)

    tim = minflux_npy['tim']
    tid = minflux_npy['tid']
    loc_x = minflux_npy['itr'][:, -1]['loc'][:, 0]
    loc_y = minflux_npy['itr'][:, -1]['loc'][:, 1]
    loc_z = minflux_npy['itr'][:, -1]['loc'][:, 2]

    unique_tids = np.unique(tid)
    new_tims = np.zeros(tim.shape)

    for current_tid in unique_tids:
        current_index = tid == current_tid
        current_tim = tim[current_index]
        new_tims[current_index] = \
            np.insert(
                      np.cumsum(np.round(np.diff(current_tim)/dt).astype(int)),
                      0,
                      0)

    data = pd.DataFrame({
        "frame": new_tims.astype(int),
        "t": dt * new_tims,
        "x": loc_x,
        "y": loc_y,
        "z": loc_z,
        "id": tid,
        "original_tim": tim
    })

    return data, dt


def find_minflux_timestep(minflux_npy):
    tim = minflux_npy['tim']
    tid = minflux_npy['tid']

    # exclude steps across different trajectories
    dt = np.diff(tim)[np.diff(tid) == 0]
    if np.any(dt == 0):
        raise ValueError("Found zero time lag!")

    # Numerics might be better if everything is O(1)
    scale = np.min(dt)
    dt = dt / scale
    mindt = np.min(dt)

    # Step 1: rough estimate through MSE
    def mse(step):
        ints = np.round(dt/step).astype(int)
        return np.sum((dt-step*ints)**2)

    res = optimize.minimize(mse, mindt,
                            bounds=[(mindt, np.inf)],
                            )
    if not res.success:
        print(res)
        raise RuntimeError

    step = res.x

    # Step 2: identify real integer steps
    udts = []
    Ns = []
    cur = 0.5*step
    while cur < np.max(dt):
        ind = (dt > cur) & (dt < cur+step)
        Ns.append(np.sum(ind))
        if Ns[-1] > 0:
            udts.append(np.mean(dt[ind]))
            cur = udts[-1] + 0.5*step
        else:
            udts.append(np.nan)
            cur += step
    udts = np.array(udts)
    Ns = np.array(Ns)

    # Step 3: fit actual best lag time
    ind = ~np.isnan(udts)
    with np.errstate(divide='ignore'):
        sigma = 1/np.sqrt(Ns[ind]-1)
    res = optimize.curve_fit(lambda x, a: a*x,
                             np.arange(len(udts))[ind]+1,
                             udts[ind],
                             sigma=sigma,
                             )

    return res[0][0]*scale
