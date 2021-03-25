from pollination.adaptive_comfort_map.entry import AdaptiveComfortMapEntryPoint
from queenbee.recipe.dag import DAG


def test_adaptive_comfort_map():
    recipe = AdaptiveComfortMapEntryPoint().queenbee
    assert recipe.name == 'adaptive-comfort-map-entry-point'
    assert isinstance(recipe, DAG)
