from collections import Counter
from dataclasses import dataclass
from typing import Dict, List
from enum import Enum
# =============== #
#  МОДЕЛИ ДАННЫХ  #
# =============== #

@dataclass
class RawWoodPlank:
    quality: float

@dataclass
class RawFabricRoll:
    quality: float

class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3

@dataclass
class PaintBucket:
    quality: float
    color: Color

@dataclass
class CatHousePart():
    quality: float
    color: Color
    
    def get_type(self):
        if self.type is None:
            raise Exception("no type")
        return self.type
    
class WoodenPartType(Enum):
    TYPE1 = 1
    TYPE2 = 2
    TYPE3 = 3

@dataclass
class WoodenHousePart(CatHousePart):
    type: WoodenPartType


class FabricPartType(Enum):
    TYPE1 = 1
    TYPE2 = 2

@dataclass
class FabricHousePart(CatHousePart):
    type: FabricPartType


@dataclass
class CatHouseSpec:
    part_counts: Dict[CatHousePart, int]
    min_quality: float
    
    def get_part_cost_by_types(self, types): 
        return sum([c for _, c in self.get_part_counts_by_types(types).items()])

    def get_part_counts_by_types(self, types):
        return {t: c for t, c in self.part_counts.items() if types is None or t in types} 

    def get_part_counts(self):
        return self.get_part_counts_by_types(None)

    def get_total_part_cost(self):
        return self.get_part_cost_by_types(None)
    
    def get_wood_cost(self):
        return self.get_part_cost_by_types(set(WoodenPartType))

    def get_fabric_cost(self):
        return self.get_part_cost_by_types(set(FabricPartType))
    
    def get_paint_cost(self):
        return self.get_total_part_cost() # на каждую деталь 1 единица краски
    
    def get_parts_by_types(self, types):
        return [t for t,c in self.get_part_counts_by_types(types).items() for _ in range(c)]
    
    def get_parts(self):
        return self.get_parts_by_types(None)



class PremiumHouseSpec(CatHouseSpec):
    def __init__(self):
        parts = {
            WoodenPartType.TYPE1: 15,
            WoodenPartType.TYPE2: 1,
            WoodenPartType.TYPE3: 3,
            FabricPartType.TYPE1: 3,
            FabricPartType.TYPE2: 2
        }
        min_quality = 0.8
        super().__init__(parts, min_quality)

class StandardHouseSpec(CatHouseSpec):
    def __init__(self):
        parts = {
            WoodenPartType.TYPE1: 10,
            WoodenPartType.TYPE2: 1,
            FabricPartType.TYPE1: 3
        }
        min_quality = None
        super().__init__(parts, min_quality)

class CatHouseType(Enum):
    STANDARD = 1
    PREMIUM = 2

class CatHouse:
    build_quality: float
    parts: List[CatHousePart]
    type: CatHouseType
    house_spec: CatHouseSpec

    def __init__(self, type: CatHouseType, spec: CatHouseSpec, build_quality: float, parts: List[CatHousePart]):
        self.parts = parts
        self.build_quality = build_quality
        self.type = type
        self.spec = spec
        self.validate_build()
    
    def validate_build(self):
        self.validate_parts()
    
    def validate_parts(self):
        if self.spec is None:
            raise Exception("no house spec")
        part_counts = Counter([p.get_type() for p in self.parts])
        if not (part_counts == self.spec.get_part_counts()):
            raise Exception(f"house parts not matching house spec parts={self.parts}")
       

class StandardCatHouse(CatHouse):
    def __init__(self, build_quality, parts):
        super().__init__(CatHouseType.STANDARD, StandardHouseSpec(), build_quality, parts)

class PremiumCatHouse(CatHouse):
    def __init__(self, build_quality, parts):
        super().__init__(CatHouseType.PREMIUM, PremiumHouseSpec(), build_quality, parts)