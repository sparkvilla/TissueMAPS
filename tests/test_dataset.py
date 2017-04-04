import time
import pytest


def _assert_resource_attribute(response_value, expected_value, resource, attr):
    __tracebackhide__ = True
    assert response_value == expected_value, (
            'Incorrect value of attribute "{attribute}" of "{resource}" resource:'
            'expected: {expected} - returned: {returned}'.format(
            attribute=attr, resource=resource,
            returned=response_value, expected=expected_value
        )
    )


def _assert_resource_count(response_value, expected_value, resource):
    __tracebackhide__ = True
    assert response_value == expected_value, (
            'Incorrect number of "{resource}" resources:'
            'expected: {expected} - returned: {returned}'.format(
            resource=resource,
            returned=response_value, expected=expected_value
        )
    )


@pytest.mark.incremental
def test_create_experiment(client, experiment_info):
    response = client.create_experiment(
        workflow_type=experiment_info.workflow_type,
        microscope_type=experiment_info.microscope_type,
        plate_format=experiment_info.plate_format,
        plate_acquisition_mode=experiment_info.plate_acquisition_mode,
    )
    _assert_resource_attribute(
        response['name'], experiment_info.name, 'experiment', 'name'
    )


@pytest.mark.incremental
def test_create_plates(client, experiment_info):
    for plate in experiment_info.plates:
        response = client.create_plate(plate.name)
        _assert_resource_attribute(
            response['name'], plate.name, 'plate', 'name'
        )
    response = client.get_plates()
    _assert_resource_count(len(response), len(experiment_info.plates), 'plate')


@pytest.mark.incremental
def test_create_acquisitions(client, experiment_info):
    for plate in experiment_info.plates:
        for acquisition in plate.acquisitions:
            response = client.create_acquisition(plate.name, acquisition.name)
            _assert_resource_attribute(
                response['name'], acquisition.name, 'acquisition', 'name'
            )
        response = client.get_acquisitions(plate.name)
        _assert_resource_count(
            len(response), len(plate.acquisitions), 'acquisition'
        )
    response = client.get_acquisitions()
    acquisitions = [a for p in experiment_info.plates for a in p.acquisitions]
    _assert_resource_count(len(response), len(acquisitions), 'acquisition')


@pytest.mark.incremental
def test_upload_microscope_files(client, experiment_info):
    for plate in experiment_info.plates:
        for acquisition in plate.acquisitions:
            client.upload_microscope_files(
                plate.name, acquisition.name, acquisition.directory
            )
            response = client.get_microscope_files(plate.name, acquisition.name)
            assert all([r['status'] == 'COMPLETE' for r in response]), (
                'Not all files have been completely uploaded for acquisition '
                '{0} of plate {1}'.format(plate.name, acquisition.name)
            )


@pytest.mark.incremental
def test_upload_workflow_description(client, experiment_info):
    client.upload_workflow_description(experiment_info.workflow_description)
    response = client.download_workflow_description()
    assert response == experiment_info.workflow_description, (
        'Workflow description was not correctly uploaded.'
    )


@pytest.mark.incremental
def test_upload_jterator_project(client, experiment_info):
    client.upload_jterator_project(**experiment_info.jterator_project)
    response = client.download_jterator_project()
    assert response == experiment_info.jterator_project, (
        'Jterator project was not correctly uploaded.'
    )


@pytest.mark.incremental
def test_submit_workflow(client, experiment_info):
    client.submit_workflow()


@pytest.mark.incremental
def test_query_workflow_status(client, experiment_info):
    start = time.time()
    while True:
        response = client.get_workflow_status(depth=1)
        if response['state'] in {'TERMINATED', 'STOPPED'}:
            assert response['exitcode'] == 0, ('Workflow failed.')
            break
        else:
            time.sleep(10)
        passed = time.time() - start
        if passed > 30 and response['state'] == 'NEW':
            raise AssertionError('Workflow submission failed.')
        elif passed > 1800:
            # TODO: half an hour might not be enough for a larger experiment
            raise AssertionError('Workflow didn\'t terminate in time.')


def test_mapobject_type_count(client, experiment_info):
    response = client.get_mapobject_types()
    _assert_resource_count(
        len(response), experiment_info.expectations.n_mapobject_types,
        'mapobject_type'
    )


def test_channel_count(client, experiment_info):
    response = client.get_channels()
    _assert_resource_count(
        len(response), experiment_info.expectations.n_channels, 'channel'
    )


def test_cycle_count(client, experiment_info):
    response = client.get_cycles()
    _assert_resource_count(
        len(response), experiment_info.expectations.n_cycles, 'cycle'
    )


def test_well_count(client, experiment_info):
    response = client.get_wells()
    _assert_resource_count(
        len(response), experiment_info.expectations.n_wells, 'well'
    )


def test_well_dimensions(client, experiment_info):
    response = client.get_wells()
    for well in response:
        _assert_resource_attribute(
            well['dimensions'], experiment_info.expectations.well_dimensions,
            'well', 'dimensions'
        )


def test_site_count(client, experiment_info):
    response = client.get_sites()
    _assert_resource_count(
        len(response), experiment_info.expectations.n_sites, 'site'
    )


def test_feature_values(client, experiment_info):
    for mapobject_type in client.get_mapobject_types():
        response = client.download_object_feature_values(mapobject_type['name'])
        expected_feature_values = experiment_info.get_expected_feature_values(
            mapobject_type['name']
        )
        assert response.equals(expected_feature_values), (
            'Feature values for object type "%s" are not correct.'
        )


def test_metadata(client, experiment_info):
    for mapobject_type in client.get_mapobject_types():
        response = client.download_object_metadata(mapobject_type['name'])
        expected_metadata = experiment_info.get_expected_metadata(
            mapobject_type['name']
        )
        assert response.equals(expected_metadata), (
            'Metadata for object type "%s" are not correct.'
        )
