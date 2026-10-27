"""Painter for the Snow kit atlas (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear [n, 3] float32, groove [n] or None).
The generator shed's wear language (gen_paint / kpp_paint helpers: chalky paint where the weather hits, worn edges,
grime in the recesses, dust on what faces up, rust runs) on the kit's finishes (snowkit_spec.ZONE_INFO): the light grey
RAL 7035 cabinet, its galvanised inside, galvanised conduits and brackets, dark hammer-finish steel, black plastic, the
grey junction box, the off-white camera, the beige monitor case with its vent slots and dark bezel, the pebble-grey
console and its brushed aluminium face, the green button caps, the orange 70s phone, the creosoted spruce pole (dark
brown low down, sun-bleached grey-brown up top, checks along the grain, a creosote bleed and the earth line at the foot,
lichen high up), white porcelain insulators, the grey-green transformer with rust runs, copper, the red clamp cover,
cable, bakelite handles, breaker modules, concrete.
Layout facts the painter relies on: every kit model stands with its underside on z = 0 of the bake (wall things are laid
out with their bottom at z = 0, desk things too), the poles from z = 0 up to 9.5 m; "low down" uses world z. Positions
otherwise only drive the noise. Noise is computed per zone on its own texels (fast with many zones)."""
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin
from gen_paint import RUST, RUST_D, _T, _common, run_m
import snowkit_spec as S

DRAFT_COL = {z: v[1] for z, v in S.ZONE_INFO.items()}        # sRGB base colours (snowkit_build --draft)
MOSS, EARTH = lin(70, 84, 46), lin(70, 58, 44)


def paint_kit(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, _ = _common(Pp, Nn, ao, 901)
    col = np.tile(lin(128, 128, 128), (n, 1)).astype(np.float32)
    gr = np.zeros(n, np.float32)
    side_all = 1.0 - np.abs(Nn[:, 2])

    for zz in np.unique(Z):
        idx = np.nonzero(Z == zz)[0]
        if not len(idx):
            continue
        P, N_ = Pp[idx], Nn[idx]
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        lo, mid, hi, u_, cv = n_lo[idx], n_mid[idx], n_hi[idx], up[idx], cav[idx]
        sd = side_all[idx]
        T = _T(lo, hi)
        g = None
        ao_i = ao[idx]

        def chips(seed, a=0.82, b=0.93):
            """sparse chips / wear on exposed surfaces (AO near 1), ~1.5 cm features"""
            return ss(0.88, 0.97, ao_i) * ss(a, b, fbm(P, 45.0, 2, seed=seed))

        if zz == S.Z_KCAB:                                   # light grey RAL 7035 powder coat, outdoors
            c = T(lin(198, 200, 194), 0.05, 0.06)
            c = mixc(c, lin(216, 216, 210), u_ * 0.25 + ss(0.55, 0.85, lo) * 0.20)                 # chalky
            streak = ss(0.56, 0.80, fbm(P * np.array([1, 1, 0.12], np.float32), 6.0, 3, seed=911))
            c = mixc(c, lin(150, 148, 138), streak * sd * 0.28)                                    # grime runs
            c = mixc(c, lin(132, 128, 116), ss(0.14, 0.0, z) * (0.35 + 0.30 * mid))                  # splash at the foot
            c = mixc(c, lin(112, 114, 112), chips(931) * 0.40)                                      # chipped paint
            rust_sp = ss(0.80, 0.91, fbm(P, 30.0, 2, seed=912))
            c = mixc(c, RUST, np.clip(chips(932, 0.76, 0.90) * ss(0.35, 0.0, z) * 0.9 + rust_sp * ss(0.30, 0.0, z) * 0.5, 0, 0.85))
            c = mixc(c, lin(168, 162, 148), u_ * ss(0.40, 0.80, mid) * 0.35)                        # dust on top
            c = mixc(c, lin(140, 140, 132), cv * 0.45)
        elif zz == S.Z_KCABIN:                               # galvanised mounting plate, shelf, inside walls
            sp = fbm(P, 90.0, 1, seed=913)
            c = T(lin(168, 172, 170), 0.08, 0.08) * (0.90 + 0.18 * sp)[:, None]
            c = mixc(c, lin(206, 208, 204), ss(0.80, 0.92, fbm(P, 25.0, 2, seed=914)) * 0.40)       # white rust
            c = mixc(c, lin(150, 146, 134), u_ * 0.30)
            c = mixc(c, lin(108, 110, 108), cv * 0.40)
        elif zz == S.Z_KGALV:                                # conduits, clamps, brackets, crossarms, the stand
            sp = fbm(P, 90.0, 1, seed=915)
            c = T(lin(150, 154, 152), 0.10, 0.08) * (0.88 + 0.22 * sp)[:, None]
            c = mixc(c, lin(196, 198, 192), ss(0.78, 0.90, fbm(P, 25.0, 2, seed=916)) * 0.40)
            c = mixc(c, RUST, run_m(P) * 0.35)
            c = mixc(c, lin(96, 82, 64), ss(0.30, 0.0, z) * 0.40)                                   # mud on runs at the ground
            c = mixc(c, lin(128, 124, 112), u_ * ss(0.4, 0.8, mid) * 0.25)
            c = mixc(c, lin(92, 94, 92), cv * 0.45)
        elif zz == S.Z_KSTEEL:                               # dark grey hammer finish
            hm = fbm(P, 60.0, 2, seed=917)
            c = T(lin(58, 60, 62), 0.08, 0.10) * (0.88 + 0.24 * hm)[:, None]
            c = mixc(c, lin(120, 122, 124), chips(933) * 0.35)
            c = mixc(c, RUST, ss(0.80, 0.92, fbm(P, 30.0, 2, seed=918)) * 0.30)
            c = mixc(c, lin(96, 92, 84), u_ * 0.15)
        elif zz == S.Z_KBLACK:                               # black plastic and rubber
            c = T(lin(34, 34, 36), 0.08, 0.10)
            c = mixc(c, lin(90, 88, 82), u_ * ss(0.4, 0.8, mid) * 0.25)
            c = mixc(c, lin(22, 22, 22), cv * 0.30)
        elif zz == S.Z_KPLAST:                               # light grey plastic (the junction box)
            c = T(lin(198, 200, 196), 0.05, 0.06)
            c = mixc(c, lin(198, 190, 160), ss(0.35, 0.75, lo) * 0.35)                              # yellowed
            c = mixc(c, lin(140, 134, 118), ss(0.07, 0.0, z) * 0.35)
            streak = ss(0.58, 0.82, fbm(P * np.array([1, 1, 0.15], np.float32), 9.0, 2, seed=919))
            c = mixc(c, lin(160, 156, 142), streak * sd * 0.18)
            c = mixc(c, lin(150, 148, 140), cv * 0.50)
        elif zz == S.Z_KCAM:                                 # off-white painted aluminium, grime from the sunshield
            c = T(lin(216, 214, 206), 0.05, 0.06)
            streak = ss(0.55, 0.80, fbm(P * np.array([1, 1, 0.10], np.float32), 12.0, 3, seed=920))
            c = mixc(c, lin(150, 146, 132), streak * sd * 0.35)
            c = mixc(c, lin(176, 170, 156), ss(0.50, 0.85, mid) * 0.25)
            c = mixc(c, lin(120, 116, 104), cv * 0.50)
            c = mixc(c, lin(150, 150, 146), chips(934) * 0.25)                                      # bare aluminium
        elif zz == S.Z_KCRT:                                 # grey-beige steel case, louvred sides
            c = T(lin(178, 172, 156), 0.06, 0.08)
            c = mixc(c, lin(176, 162, 124), ss(0.40, 0.80, lo) * 0.30)                              # yellowed
            vent_side = (np.abs(N_[:, 0]) > 0.8) & (z > 0.16) & (z < 0.30)
            slot = dist_periodic(z, 0.022, 0.011) < 0.0065
            vent = vent_side & slot
            c = np.where(vent[:, None], lin(40, 38, 34), c)
            c = mixc(c, lin(150, 144, 128), u_ * 0.30)                                              # dust on top
            c = mixc(c, lin(112, 106, 92), cv * 0.40)
            g = np.where(vent_side, gline(dist_periodic(z, 0.022, 0.011), 0.013, aa) * 0.8, 0.0)
        elif zz == S.Z_KBEZEL:                               # dark grey bezel
            c = T(lin(70, 70, 72), 0.05, 0.06)
            c = mixc(c, lin(104, 100, 92), u_ * 0.25)
            c = mixc(c, lin(46, 46, 48), cv * 0.35)
        elif zz == S.Z_KCONS:                                # pebble grey console housing
            c = T(lin(172, 168, 152), 0.06, 0.08)
            c = mixc(c, lin(112, 110, 102), chips(935) * 0.35)
            c = mixc(c, lin(150, 144, 126), u_ * ss(0.4, 0.8, mid) * 0.25)
            c = mixc(c, lin(120, 116, 104), cv * 0.45)
        elif zz == S.Z_KALU:                                 # brushed aluminium front panel
            br = fbm(P * np.array([0.02, 6.0, 6.0], np.float32), 30.0, 2, seed=921)              # brushed along x
            c = T(lin(178, 180, 184), 0.04, 0.05) * (0.90 + 0.16 * br)[:, None]
            c = mixc(c, lin(130, 132, 136), ss(0.72, 0.86, fbm(P, 14.0, 2, seed=922)) * 0.25)      # finger smudges
            c = mixc(c, lin(110, 112, 116), cv * 0.45)
        elif zz == S.Z_KBTN:                                 # green push-button caps, glossy
            c = T(lin(46, 150, 66), 0.05, 0.06) * (0.80 + 0.20 * u_)[:, None]
            c = mixc(c, lin(112, 204, 124), u_ * 0.30)
            c = mixc(c, lin(20, 70, 30), cv * 0.40)
        elif zz == S.Z_KPHONE:                               # orange 70s phone plastic
            c = T(lin(204, 100, 42), 0.06, 0.08)
            c = mixc(c, lin(222, 128, 70), u_ * 0.22)                                               # faded on top
            c = mixc(c, lin(140, 74, 36), ss(0.70, 0.88, fbm(P, 18.0, 2, seed=923)) * 0.30)        # greasy where held
            c = mixc(c, lin(120, 62, 30), cv * 0.50)
        elif zz == S.Z_KPOLE:                                # creosoted spruce pole
            h = ss(0.3, 8.5, z)
            base = lin(64, 46, 32)[None, :] * (1 - h)[:, None] + lin(118, 104, 88)[None, :] * h[:, None]
            grain = fbm(P * np.array([5.0, 5.0, 0.18], np.float32), 8.0, 3, seed=924)          # along the pole
            c = base * (0.84 + 0.30 * grain)[:, None] * (0.92 + 0.16 * (lo - 0.5))[:, None]
            k = fbm(P * np.array([9.0, 9.0, 0.06], np.float32), 6.0, 2, seed=925)              # checks (cracks)
            crack = (1.0 - ss(0.008, 0.020, np.abs(k - 0.5))) * sd
            c = mixc(c, lin(30, 22, 16), crack * 0.75)
            c = mixc(c, lin(38, 28, 20), ss(1.4, 0.2, z) * 0.55 * (0.6 + 0.4 * mid))               # creosote bleed
            c = mixc(c, EARTH, ss(0.25, 0.0, z) * 0.60)                                             # the earth line
            c = mixc(c, lin(120, 128, 100), ss(0.78, 0.90, fbm(P, 10.0, 2, seed=926)) * 0.35 * h)  # lichen high up
            c = np.where((N_[:, 2] > 0.8)[:, None], mixc(c, lin(112, 98, 80), np.full(len(z), 0.6)), c)   # the cut top
            c = mixc(c, lin(40, 32, 24), cv * 0.45)
            g = crack * 0.6
        elif zz == S.Z_KPORC:                                # white glazed porcelain
            c = T(lin(224, 222, 212), 0.04, 0.05)
            c = mixc(c, lin(140, 136, 124), u_ * 0.45 * (0.5 + 0.5 * mid))                          # grime on the sheds
            c = mixc(c, lin(150, 148, 140), cv * 0.40)
        elif zz == S.Z_KTRAFO:                               # grey-green tank, rust runs from the lid and the seams
            c = T(lin(112, 120, 108), 0.10, 0.10)
            c = mixc(c, lin(136, 142, 132), u_ * 0.25)
            rr = ss(0.62, 0.84, fbm(P * np.array([1, 1, 0.15], np.float32), 7.0, 3, seed=927))
            c = mixc(c, RUST, rr * sd * 0.45)
            c = mixc(c, RUST_D, chips(936, 0.78, 0.92) * 0.55)
            c = mixc(c, lin(70, 74, 66), cv * 0.50)
        elif zz == S.Z_KCOPPER:                              # copper and brass
            c = T(lin(176, 104, 60), 0.10, 0.14)
            c = mixc(c, lin(96, 130, 104), ss(0.70, 0.88, fbm(P, 30.0, 2, seed=928)) * 0.50)       # verdigris
            c = mixc(c, lin(70, 44, 30), cv * 0.60)
        elif zz == S.Z_KREDC:                                # red insulating cover of the + clamp
            c = T(lin(176, 32, 26), 0.06, 0.08)
            c = mixc(c, lin(120, 96, 80), u_ * 0.18)
            c = mixc(c, lin(90, 24, 20), cv * 0.50)
        elif zz == S.Z_KCABLE:                               # black rubber cable
            c = T(lin(30, 30, 30), 0.08, 0.12)
            c = mixc(c, lin(90, 86, 78), u_ * 0.25 * (0.5 + 0.5 * mid))
        elif zz == S.Z_KHANDLE:                              # black bakelite handles and knobs
            c = T(lin(28, 28, 30), 0.06, 0.08)
            c = mixc(c, lin(74, 56, 44), chips(937) * 0.35)                                         # worn brownish
            c = mixc(c, lin(70, 70, 72), u_ * 0.15)
        elif zz == S.Z_KBRKR:                                # white breaker modules (model the toggles)
            c = T(lin(226, 224, 216), 0.04, 0.05)
            c = mixc(c, lin(214, 204, 172), ss(0.40, 0.80, lo) * 0.30)
            c = mixc(c, lin(170, 164, 150), u_ * 0.30)
            c = mixc(c, lin(150, 148, 140), cv * 0.45)
        elif zz == S.Z_KCONC:                                # concrete
            c = T(lin(132, 130, 124), 0.16, 0.22)
            c = mixc(c, lin(86, 82, 76), ss(0.06, 0.0, z) * 0.60 + cv * 0.40)
            c = mixc(c, lin(150, 148, 140), u_ * 0.20)
            c = mixc(c, MOSS, ss(0.80, 0.90, fbm(P, 8.0, 2, seed=929)) * u_ * 0.30)
        else:                                                # an unknown zone: grey, so it shows in the sheet
            c = T(lin(128, 128, 128), 0.05, 0.05)
        col[idx] = np.clip(c, 0, 1)
        if g is not None:
            gr[idx] = np.clip(g, 0, 1)
    return col.astype(np.float32), gr


painter = paint_kit
