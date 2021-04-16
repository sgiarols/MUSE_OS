from pytest import mark


def modify_technodata_timeslices(model_path, sector, process_name, utilization_factors):
    import pandas as pd

    technodata_timeslices = pd.read_csv(
        model_path / "technodata" / sector / "TechnodataTimeslices.csv"
    )

    technodata_timeslices.loc[
        technodata_timeslices["ProcessName"] == process_name[0], "UtilizationFactor"
    ] = utilization_factors[0]

    technodata_timeslices.loc[
        technodata_timeslices["ProcessName"] == process_name[1], "UtilizationFactor"
    ] = utilization_factors[1]

    return technodata_timeslices


@mark.parametrize("utilization_factors", [([0.1], [1]), ([1], [0.1]), ([0.001], [1])])
@mark.parametrize("process_name", [("gasCCGT", "windturbine")])
def test_fullsim_timeslices(tmpdir, utilization_factors, process_name):
    from muse import examples
    from muse.mca import MCA
    import pandas as pd
    from operator import le, ge

    sector = "power"

    # Copy the model inputs to tmpdir
    model_path = examples.copy_model(
        name="default_timeslice", path=tmpdir, overwrite=True
    )

    technodata_timeslices = modify_technodata_timeslices(
        model_path=model_path,
        sector=sector,
        process_name=process_name,
        utilization_factors=utilization_factors,
    )

    technodata_timeslices.to_csv(
        model_path / "technodata" / sector / "TechnodataTimeslices.csv", index=False
    )

    with tmpdir.as_cwd():
        MCA.factory(model_path / "settings.toml").run()

    MCACapacity = pd.read_csv(tmpdir / "Results/MCACapacity.csv")

    if utilization_factors[0] > utilization_factors[1]:
        operator = ge
    else:
        operator = le

    assert operator(
        len(
            MCACapacity[
                (MCACapacity.sector == sector)
                & (MCACapacity.technology == process_name[0])
            ]
        ),
        len(
            MCACapacity[
                (MCACapacity.sector == sector)
                & (MCACapacity.technology == process_name[1])
            ]
        ),
    )


@mark.parametrize(
    "utilization_factors",
    [
        ([0, 0, 1, 1, 1, 1], [1, 1, 1, 1, 1, 1]),
        ([1, 1, 1, 1, 1, 1], [1, 1, 0, 0, 1, 1]),
    ],
)
@mark.parametrize("process_name", [("gasCCGT", "windturbine")])
@mark.parametrize("output", ["Supply_Timeslice", "Consumption_Timeslice"])
def test_zero_utilization_factor_supply_timeslice(
    tmpdir, utilization_factors, process_name, output
):
    from muse import examples
    from muse.mca import MCA
    import pandas as pd
    import glob

    sector = "power"

    # Copy the model inputs to tmpdir
    model_path = examples.copy_model(
        name="default_timeslice", path=tmpdir, overwrite=True
    )

    technodata_timeslices = modify_technodata_timeslices(
        model_path=model_path,
        sector=sector,
        process_name=process_name,
        utilization_factors=utilization_factors,
    )

    technodata_timeslices.to_csv(
        model_path / "technodata" / sector / "TechnodataTimeslices.csv", index=False
    )

    with tmpdir.as_cwd():
        MCA.factory(model_path / "settings.toml").run()

    path = str(tmpdir / "Results" / "Power" / output)
    all_files = glob.glob(path + "/*.csv")

    results = []
    for filename in all_files:
        result = pd.read_csv(filename, index_col=None, header=0)
        results.append(result)

    output = pd.concat(results, axis=0, ignore_index=True)

    zero_utilization_factors = [i for i, e in enumerate(utilization_factors) if e == 0]

    assert (
        len(
            output[
                (
                    output.timeslice.isin(zero_utilization_factors)
                    & (output.technology == process_name)
                )
            ]
        )
        == 0
    )


def change_timeslice_levels(model_path, sector, process_name, utilization_factors):
    import pandas as pd

    technodata_timeslices = pd.read_csv(
        model_path / "technodata" / sector / "TechnodataTimeslices.csv"
    )

    technodata_timeslices = technodata_timeslices.drop(columns="day")

    return technodata_timeslices


@mark.parametrize(
    "utilization_factors",
    [
        ([0, 0, 1, 1, 1, 1], [1, 1, 1, 1, 1, 1]),
        ([1, 1, 1, 1, 1, 1], [1, 1, 0, 0, 1, 1]),
    ],
)
@mark.parametrize("process_name", [("gasCCGT", "windturbine")])
@mark.parametrize("output", ["Supply_Timeslice", "Consumption_Timeslice"])
def test_dynamic_timeslice_levels(tmpdir, utilization_factors, process_name, output):
    from muse import examples
    from muse.mca import MCA
    import pandas as pd
    from toml import load, dump
    import glob

    sector = "power"

    # Copy the model inputs to tmpdir
    model_path = examples.copy_model(
        name="default_timeslice", path=tmpdir, overwrite=True
    )

    technodata_timeslices = change_timeslice_levels(
        model_path=model_path,
        sector=sector,
        process_name=process_name,
        utilization_factors=utilization_factors,
    )
    technodata_timeslices.to_csv(
        model_path / "technodata" / sector / "TechnodataTimeslices.csv", index=False
    )

    settings = load(model_path / "settings.toml")
    print(settings["timeslices"])

    settings["timeslices"] = {
        "all-year": settings["timeslices"]["all-year"]["all-week"]
    }

    dump(settings, (model_path / "modified_settings.toml").open("w"))

    with tmpdir.as_cwd():
        MCA.factory(model_path / "modified_settings.toml").run()

    path = str(tmpdir / "Results" / "Power" / output)
    all_files = glob.glob(path + "/*.csv")

    results = []
    for filename in all_files:
        result = pd.read_csv(filename, index_col=None, header=0)
        results.append(result)

    output = pd.concat(results, axis=0, ignore_index=True)

    zero_utilization_factors = [i for i, e in enumerate(utilization_factors) if e == 0]

    assert (
        len(
            output[
                (
                    output.timeslice.isin(zero_utilization_factors)
                    & (output.technology == process_name)
                )
            ]
        )
        == 0
    )
