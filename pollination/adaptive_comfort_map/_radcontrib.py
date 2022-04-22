from pollination_dsl.dag import Inputs, DAG, task
from dataclasses import dataclass
from typing import Dict, List

from pollination.honeybee_radiance.contrib import DaylightContribution
from pollination.honeybee_radiance.coefficient import DaylightCoefficient
from pollination.honeybee_radiance.sky import SubtractSkyMatrix
from pollination.ladybug_comfort.map import IrradianceContribMap


@dataclass
class RadianceContribEntryPoint(DAG):
    """Entry point for Radiance calculations for comfort mapping."""

    # inputs
    radiance_parameters = Inputs.str(
        description='Radiance parameters for ray tracing.',
        default='-ab 2 -ad 5000 -lw 2e-05',
    )

    octree_file_spec = Inputs.file(
        description='A Radiance octree file with a specular version of the '
        'window group.', extensions=['oct']
    )

    octree_file_diff = Inputs.file(
        description='A Radiance octree file with a diffuse version of the window group.',
        extensions=['oct']
    )

    octree_file_with_suns = Inputs.file(
        description='A Radiance octree file with sun modifiers.',
        extensions=['oct']
    )

    group_name = Inputs.str(
        description='Name for the dynamic aperture group being simulated.'
    )

    grid_name = Inputs.str(
        description='Sensor grid file name (used to name the final result files).'
    )

    sensor_grid = Inputs.file(
        description='Sensor grid file.',
        extensions=['pts']
    )

    ref_sensor_grid = Inputs.file(
        description='Reflected Sensor grid file.',
        extensions=['pts']
    )

    sensor_count = Inputs.int(
        description='Number of sensors in the input sensor grid.'
    )

    sky_dome = Inputs.file(
        description='Path to sky dome file.'
    )

    sky_matrix = Inputs.file(
        description='Path to total sky matrix file.'
    )

    sky_matrix_direct = Inputs.file(
        description='Path to direct skymtx file (gendaymtx -d).'
    )

    sun_modifiers = Inputs.file(
        description='A file with sun modifiers.'
    )

    result_sql = Inputs.file(
        description='A SQLite file that was generated by EnergyPlus and contains '
        'window transmittance results.',
        extensions=['sql', 'db', 'sqlite']
    )

    sun_up_hours = Inputs.file(
        description='A sun-up-hours.txt file output by Radiance and aligns with the '
        'input irradiance files.'
    )

    @task(template=DaylightContribution)
    def direct_sun_group(
        self,
        grid=grid_name,
        group=group_name,
        radiance_parameters=radiance_parameters,
        fixed_radiance_parameters='-aa 0.0 -I -ab 0 -dc 1.0 -dt 0.0 -dj 0.0 -dr 0',
        sensor_count=sensor_count,
        modifiers=sun_modifiers,
        sensor_grid=sensor_grid,
        conversion='0.265 0.670 0.065',
        output_format='a',  # make it ascii so we expose the file as a separate output
        header='remove',  # remove header to make it process-able later
        scene_file=octree_file_with_suns
    ):
        return [
            {
                'from': DaylightContribution()._outputs.result_file,
                'to': 'dynamic/initial/{{self.group}}/direct_spec/{{self.grid}}.ill'
            }
        ]

    @task(template=DaylightCoefficient)
    def direct_sky_group(
        self,
        grid=grid_name,
        group=group_name,
        radiance_parameters=radiance_parameters,
        fixed_radiance_parameters='-aa 0.0 -I -ab 1 -c 1 -faf',
        sensor_count=sensor_count,
        sky_matrix=sky_matrix_direct,
        sky_dome=sky_dome,
        sensor_grid=sensor_grid,
        conversion='0.265 0.670 0.065',  # divide by 179
        scene_file=octree_file_spec
    ):
        return [
            {
                'from': DaylightCoefficient()._outputs.result_file,
                'to': 'dynamic/initial/{{self.group}}/direct_sky/{{self.grid}}.ill'
            }
        ]

    @task(template=DaylightCoefficient)
    def total_sky_spec_group(
        self,
        grid=grid_name,
        group=group_name,
        radiance_parameters=radiance_parameters,
        fixed_radiance_parameters='-aa 0.0 -I -c 1 -faf',
        sensor_count=sensor_count,
        sky_matrix=sky_matrix,
        sky_dome=sky_dome,
        sensor_grid=sensor_grid,
        conversion='0.265 0.670 0.065',  # divide by 179
        scene_file=octree_file_spec
    ):
        return [
            {
                'from': DaylightCoefficient()._outputs.result_file,
                'to': 'dynamic/initial/{{self.group}}/total_sky/{{self.grid}}.ill'
            }
        ]

    @task(template=SubtractSkyMatrix, needs=[total_sky_spec_group, direct_sky_group])
    def output_matrix_math_group(
        self,
        grid=grid_name,
        group=group_name,
        total_sky_matrix=total_sky_spec_group._outputs.result_file,
        direct_sky_matrix=direct_sky_group._outputs.result_file
    ):
        return [
            {
                'from': SubtractSkyMatrix()._outputs.results_file,
                'to': 'dynamic/initial/{{self.group}}/indirect_spec/{{self.grid}}.ill'
            }
        ]

    @task(template=DaylightCoefficient)
    def ground_reflected_sky_spec_group(
        self,
        grid=grid_name,
        group=group_name,
        radiance_parameters=radiance_parameters,
        fixed_radiance_parameters='-aa 0.0 -I -c 1',
        sensor_count=sensor_count,
        sky_matrix=sky_matrix,
        sky_dome=sky_dome,
        sensor_grid=ref_sensor_grid,
        conversion='0.265 0.670 0.065',  # divide by 179
        output_format='a',  # make it ascii so we expose the file as a separate output
        header='remove',  # remove header to make it process-able later
        scene_file=octree_file_spec
    ):
        return [
            {
                'from': DaylightCoefficient()._outputs.result_file,
                'to': 'dynamic/initial/{{self.group}}/reflected_spec/{{self.grid}}.ill'
            }
        ]

    @task(template=DaylightCoefficient)
    def total_sky_diff_group(
        self,
        grid=grid_name,
        group=group_name,
        radiance_parameters=radiance_parameters,
        fixed_radiance_parameters='-aa 0.0 -I -c 1',
        sensor_count=sensor_count,
        sky_matrix=sky_matrix,
        sky_dome=sky_dome,
        sensor_grid=sensor_grid,
        conversion='0.265 0.670 0.065',  # divide by 179
        output_format='a',  # make it ascii so we expose the file as a separate output
        header='remove',  # remove header to make it process-able later
        scene_file=octree_file_diff
    ):
        return [
            {
                'from': DaylightCoefficient()._outputs.result_file,
                'to': 'dynamic/initial/{{self.group}}/total_diff/{{self.grid}}.ill'
            }
        ]

    @task(template=DaylightCoefficient)
    def ground_reflected_sky_diff_group(
        self,
        grid=grid_name,
        group=group_name,
        radiance_parameters=radiance_parameters,
        fixed_radiance_parameters='-aa 0.0 -I -c 1',
        sensor_count=sensor_count,
        sky_matrix=sky_matrix,
        sky_dome=sky_dome,
        sensor_grid=ref_sensor_grid,
        conversion='0.265 0.670 0.065',  # divide by 179
        output_format='a',  # make it ascii so we expose the file as a separate output
        header='remove',  # remove header to make it process-able later
        scene_file=octree_file_diff
    ):
        return [
            {
                'from': DaylightCoefficient()._outputs.result_file,
                'to': 'dynamic/initial/{{self.group}}/reflected_diff/{{self.grid}}.ill'
            }
        ]

    @task(
        template=IrradianceContribMap,
        needs=[
            direct_sun_group, output_matrix_math_group, ground_reflected_sky_spec_group,
            total_sky_diff_group, ground_reflected_sky_diff_group
        ]
    )
    def create_irradiance_contrib_map(
        self,
        result_sql=result_sql,
        direct_specular=direct_sun_group._outputs.result_file,
        indirect_specular=output_matrix_math_group._outputs.results_file,
        ref_specular=ground_reflected_sky_spec_group._outputs.result_file,
        indirect_diffuse=total_sky_diff_group._outputs.result_file,
        ref_diffuse=ground_reflected_sky_diff_group._outputs.result_file,
        sun_up_hours=sun_up_hours,
        aperture_id=group_name,
        grid=grid_name
    ) -> List[Dict]:
        return [
            {
                'from': IrradianceContribMap()._outputs.result_folder,
                'to': 'dynamic/final/{{self.grid}}/{{self.aperture_id}}'
            }
        ]