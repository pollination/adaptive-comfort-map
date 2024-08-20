from pollination_dsl.dag import Inputs, GroupedDAG, task, Outputs
from dataclasses import dataclass
from typing import Dict, List

from pollination.ladybug_comfort.epw import AirSpeedJson
from pollination.ladybug_comfort.map import ShortwaveMrtMap, LongwaveMrtMap, AirMap, Tcp
from pollination.ladybug_comfort.mtx import AdaptiveMtx


@dataclass
class ComfortMappingEntryPoint(GroupedDAG):
    """Entry point for Comfort calculations."""

    # inputs
    epw = Inputs.file(
        description='Weather file used for the comfort map.',
        extensions=['epw']
    )

    result_sql = Inputs.file(
        description='A SQLite file that was generated by EnergyPlus and contains '
        'hourly or sub-hourly thermal comfort results.',
        extensions=['sql', 'db', 'sqlite']
    )

    grid_name = Inputs.str(
        description='Sensor grid file name (used to name the final result files).'
    )

    enclosure_info = Inputs.file(
        description='A JSON file containing information about the radiant '
        'enclosure that sensor points belong to.',
        extensions=['json']
    )

    view_factors = Inputs.file(
        description='A CSV of spherical view factors to the surfaces in the result-sql.',
        extensions=['csv']
    )

    modifiers = Inputs.file(
        description='Path to a modifiers file that aligns with the view-factors.',
        extensions=['mod', 'txt']
    )

    indirect_irradiance = Inputs.file(
        description='An .ill containing the indirect irradiance for each sensor.',
        extensions=['ill', 'irr']
    )

    direct_irradiance = Inputs.file(
        description='An .ill containing direct irradiance for each sensor.',
        extensions=['ill', 'irr']
    )

    ref_irradiance = Inputs.file(
        description='An .ill containing ground-reflected irradiance for each '
        'sensor.', extensions=['ill', 'irr']
    )

    sun_up_hours = Inputs.file(
        description='A sun-up-hours.txt file output by Radiance and aligns with the '
        'input irradiance files.'
    )

    contributions = Inputs.folder(
        description='An optional folder containing sub-folders of irradiance '
        'contributions from dynamic aperture groups. There should be one sub-folder '
        'per window group and each one should contain three .ill files named '
        'direct.ill, indirect.ill and reflected.ill. If specified, these will be '
        'added to the irradiance inputs before computing shortwave MRT deltas.',
        optional=True
    )

    transmittance_contribs = Inputs.folder(
        description='An optional folder containing a transmittance schedule JSON '
        'and sub-folders of irradiance results that exclude the shade from the '
        'calculation. There should be one sub-folder per window groups and each '
        'one should contain three .ill files named direct.ill, indirect.ill and '
        'reflected.ill. If specified, these will be added to the irradiance inputs '
        'before computing shortwave MRT deltas.', optional=True
    )

    trans_schedules = Inputs.file(
        description='A schedule JSON that contains fractional schedule values '
        'for each shade transmittance schedule in the model.'
    )

    occ_schedules = Inputs.file(
        description='A JSON file containing occupancy schedules derived from '
        'the input model.'
    )

    run_period = Inputs.str(
        description='An AnalysisPeriod string to set the start and end dates of '
        'the simulation (eg. "6/21 to 9/21 between 0 and 23 @1"). If None, '
        'the simulation will be annual.', default=''
    )

    air_speed = Inputs.file(
        description='A CSV file containing a single number for air speed in m/s or '
        'several rows of air speeds that align with the length of the run period.',
        optional=True
    )

    prevailing = Inputs.file(
        description='A CSV file with with a list of prevailing outdoor temperatures '
        'in a single row (one temperautre per column).', extensions=['csv']
    )

    solarcal_parameters = Inputs.str(
        description='A SolarCalParameter string to customize the assumptions of '
        'the SolarCal model.', default='--posture seated --sharp 135 '
        '--absorptivity 0.7 --emissivity 0.95'
    )

    comfort_parameters = Inputs.str(
        description='An AdaptiveParameter string to customize the assumptions of '
        'the Adaptive comfort model.', default='--standard ASHRAE-55'
    )

    @task(template=LongwaveMrtMap)
    def create_longwave_mrt_map(
        self,
        result_sql=result_sql,
        view_factors=view_factors,
        modifiers=modifiers,
        enclosure_info=enclosure_info,
        epw=epw,
        run_period=run_period,
        name=grid_name,
        output_format='binary'
    ) -> List[Dict]:
        return [
            {
                'from': LongwaveMrtMap()._outputs.longwave_mrt_map,
                'to': 'conditions/longwave_mrt/{{self.name}}.csv'
            }
        ]

    @task(template=ShortwaveMrtMap)
    def create_shortwave_mrt_map(
        self,
        epw=epw,
        indirect_irradiance=indirect_irradiance,
        direct_irradiance=direct_irradiance,
        ref_irradiance=ref_irradiance,
        sun_up_hours=sun_up_hours,
        contributions=contributions,
        transmittance_contribs=transmittance_contribs,
        trans_schedules=trans_schedules,
        solarcal_par=solarcal_parameters,
        run_period=run_period,
        name=grid_name,
        output_format='binary'
    ) -> List[Dict]:
        return [
            {
                'from': ShortwaveMrtMap()._outputs.shortwave_mrt_map,
                'to': 'conditions/shortwave_mrt/{{self.name}}.csv'
            }
        ]

    @task(template=AirMap)
    def create_air_temperature_map(
        self,
        result_sql=result_sql,
        enclosure_info=enclosure_info,
        epw=epw,
        run_period=run_period,
        metric='air-temperature',
        name=grid_name,
        output_format='binary'
    ) -> List[Dict]:
        return [
            {
                'from': AirMap()._outputs.air_map,
                'to': 'conditions/air_temperature/{{self.name}}.csv'
            }
        ]

    @task(template=AirSpeedJson)
    def create_air_speed_json(
        self, epw=epw, enclosure_info=enclosure_info, multiply_by=0.5,
        indoor_air_speed=air_speed, run_period=run_period, name=grid_name
    ) -> List[Dict]:
        return [
            {
                'from': AirSpeedJson()._outputs.air_speeds,
                'to': 'conditions/air_speed/{{self.name}}.json'
            }
        ]

    @task(
        template=AdaptiveMtx,
        needs=[
            create_longwave_mrt_map, create_shortwave_mrt_map,
            create_air_temperature_map, create_air_speed_json
        ]
    )
    def process_adaptive_matrix(
        self,
        air_temperature_mtx=create_air_temperature_map._outputs.air_map,
        rad_temperature_mtx=create_longwave_mrt_map._outputs.longwave_mrt_map,
        rad_delta_mtx=create_shortwave_mrt_map._outputs.shortwave_mrt_map,
        air_speed_json=create_air_speed_json._outputs.air_speeds,
        prevailing_temperature=prevailing,
        comfort_par=comfort_parameters,
        output_format='binary',
        name=grid_name
    ) -> List[Dict]:
        return [
            {
                'from': AdaptiveMtx()._outputs.temperature_map,
                'to': 'results/temperature/{{self.name}}.csv'
            },
            {
                'from': AdaptiveMtx()._outputs.condition_map,
                'to': 'results/condition/{{self.name}}.csv'
            },
            {
                'from': AdaptiveMtx()._outputs.deg_from_neutral_map,
                'to': 'results/condition_intensity/{{self.name}}.csv'
            }
        ]

    @task(
        template=Tcp,
        needs=[process_adaptive_matrix]
    )
    def compute_tcp(
        self,
        condition_csv=process_adaptive_matrix._outputs.condition_map,
        enclosure_info=enclosure_info,
        occ_schedule_json=occ_schedules,
        name=grid_name
    ) -> List[Dict]:
        return [
            {'from': Tcp()._outputs.tcp, 'to': 'metrics/TCP/{{self.name}}.csv'},
            {'from': Tcp()._outputs.hsp, 'to': 'metrics/HSP/{{self.name}}.csv'},
            {'from': Tcp()._outputs.csp, 'to': 'metrics/CSP/{{self.name}}.csv'}
        ]

    results_folder = Outputs.folder(source='results')

    conditions = Outputs.folder(source='conditions')

    metrics = Outputs.folder(source='metrics')
