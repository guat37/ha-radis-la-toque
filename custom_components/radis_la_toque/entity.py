"""Base entity for Radis la Toque."""
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .coordinator import RadisLaToqueCoordinator

class RadisLaToqueEntity(CoordinatorEntity[RadisLaToqueCoordinator]):
    _attr_has_entity_name = True
    def __init__(self, coordinator: RadisLaToqueCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, coordinator.code)}, name=coordinator.restaurant_name, manufacturer="RESTORIA / Radis la Toque", configuration_url=f"https://www.radislatoque.fr/restaurants/{coordinator.code}")
