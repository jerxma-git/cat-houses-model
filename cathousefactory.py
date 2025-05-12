from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Union
import simpy
import random
import math
from sortedcontainers import SortedList

from models import CatHouse, CatHousePart, CatHouseSpec, CatHouseType, PremiumCatHouse, RawWoodPlank, RawFabricRoll, PaintBucket, StandardCatHouse
from models import Color, WoodenHousePart, WoodenPartType, FabricHousePart, FabricPartType
from models import StandardHouseSpec, PremiumHouseSpec
from customrng import CustomRNG

class CatFactoryConfig:
    PLANNED_HOUSES_NUM: float
    PLANNED_PREMIUM_RATIO: float 

    HOUSE_SPECS: Dict[CatHouseType, CatHouseSpec]

    PLANNED_HOUSES_NUMS: Dict[CatHouseType, int]

    MIN_PREMIUM_WOOD_QUALITY: float
    MIN_PREMIUM_FABRIC_QUALITY: float
    MIN_PREMIUM_PAINT_QUALITY: float

    MIN_PREMIUM_WOODEN_PART_QUALITY: float 
    MIN_PREMIUM_FABRIC_PART_QUALITY: float 

    BROKEN_PLANKS_RATIO: float
    BROKEN_ROLLS_RATIO: float

    BROKEN_PARTS_RATIO: float

    BUILDERS_NUM: int
    CATS_NUM: int

    MAX_ENTRY_TIME: int
    MIN_TIME_INSIDE: int
    MAX_TEST_TIME: int
    
    DEFAULT_RNG_CONFIG = {
        "material_delivery_time": {
            "mu": 120,
            "sigma": 20
        },
        "wooden_processing_time": {
            "mu": 1,
            "sigma": 2,
            "min_time": 0.5,
            "max_time": 6
        },
        "fabric_processing_time": {
            "mu": 0.5,
            "sigma": 1,
            "min_time": 0.25,
            "max_time": 3
        },
        "raw_material_quality": {
            CatHouseType.STANDARD: {
                "mu": 0.7,
                "sigma": 0.1
            },
            CatHouseType.PREMIUM: {
                "mu": 0.85,
                "sigma": 0.05
            },
        },
        "house_build_quality": {
            CatHouseType.STANDARD: {
                "mu": 0.7,
                "sigma": 0.1
            },
            CatHouseType.PREMIUM: {
                "mu": 0.85,
                "sigma": 0.05
            },
        },
        "entry_timing": {
            "scale": 15,
            "base_multiplier": 1.3
        },
        "time_inside": {
            "base_mu": 20,
            "sigma": 5
        }
    }
    RNG_CONFIG: Dict

    def __init__(
            self,
            PLANNED_HOUSES_NUM = 100,
            PLANNED_PREMIUM_RATIO = 0.5,
            MIN_PREMIUM_WOOD_QUALITY = 0.7,
            MIN_PREMIUM_FABRIC_QUALITY = 0.7,
            MIN_PREMIUM_PAINT_QUALITY = 0.7,
            MIN_PREMIUM_WOODEN_PART_QUALITY = 0.7,
            MIN_PREMIUM_FABRIC_PART_QUALITY = 0.7,
            BROKEN_PLANKS_RATIO = 0.02,
            BROKEN_ROLLS_RATIO = 0.02,
            BROKEN_PARTS_RATIO = 0.02,
            BUILDERS_NUM = 4,
            CATS_NUM = 4,
            MAX_ENTRY_TIME = 30,
            MIN_TIME_INSIDE = 5,
            MAX_TEST_TIME = 60,
            RNG_CONFIG = DEFAULT_RNG_CONFIG,
            DETAIL_PROCESSING_TIME_OVERRIDE = None, # костыль для удобства
        ):
        self.PLANNED_HOUSES_NUM = PLANNED_HOUSES_NUM
        self.PLANNED_PREMIUM_RATIO = PLANNED_PREMIUM_RATIO
        self.MIN_PREMIUM_WOOD_QUALITY = MIN_PREMIUM_WOOD_QUALITY
        self.MIN_PREMIUM_FABRIC_QUALITY = MIN_PREMIUM_FABRIC_QUALITY
        self.MIN_PREMIUM_PAINT_QUALITY = MIN_PREMIUM_PAINT_QUALITY
        self.MIN_PREMIUM_WOODEN_PART_QUALITY = MIN_PREMIUM_WOODEN_PART_QUALITY
        self.MIN_PREMIUM_FABRIC_PART_QUALITY = MIN_PREMIUM_FABRIC_PART_QUALITY
        self.BROKEN_PLANKS_RATIO = BROKEN_PLANKS_RATIO
        self.BROKEN_ROLLS_RATIO = BROKEN_ROLLS_RATIO
        self.BROKEN_PARTS_RATIO = BROKEN_PARTS_RATIO
        self.BUILDERS_NUM = BUILDERS_NUM
        self.CATS_NUM = CATS_NUM
        self.MAX_ENTRY_TIME = MAX_ENTRY_TIME
        self.MIN_TIME_INSIDE = MIN_TIME_INSIDE
        self.MAX_TEST_TIME = MAX_TEST_TIME
        self.RNG_CONFIG = RNG_CONFIG
    

        # костыли
        if DETAIL_PROCESSING_TIME_OVERRIDE is not None:
            self.RNG_CONFIG['wooden_processing_time']['mu'] = DETAIL_PROCESSING_TIME_OVERRIDE
            self.RNG_CONFIG['wooden_processing_time']['sigma'] = DETAIL_PROCESSING_TIME_OVERRIDE / 5
            self.RNG_CONFIG['wooden_processing_time']['min_time'] = DETAIL_PROCESSING_TIME_OVERRIDE / 2
            self.RNG_CONFIG['wooden_processing_time']['max_time'] = DETAIL_PROCESSING_TIME_OVERRIDE * 6
        if DETAIL_PROCESSING_TIME_OVERRIDE is not None:
            self.RNG_CONFIG['fabric_processing_time']['mu'] = DETAIL_PROCESSING_TIME_OVERRIDE / 2
            self.RNG_CONFIG['fabric_processing_time']['sigma'] = DETAIL_PROCESSING_TIME_OVERRIDE / 10
            self.RNG_CONFIG['fabric_processing_time']['min_time'] = DETAIL_PROCESSING_TIME_OVERRIDE / 4
            self.RNG_CONFIG['fabric_processing_time']['max_time'] = DETAIL_PROCESSING_TIME_OVERRIDE * 3


        self.PLANNED_HOUSES_NUMS = {
            CatHouseType.PREMIUM: self.get_planned_premium_houses_num(),
            CatHouseType.STANDARD: self.get_planned_standard_houses_num()
        }

        self.HOUSE_SPECS = {
            CatHouseType.STANDARD: StandardHouseSpec(), 
            CatHouseType.PREMIUM: PremiumHouseSpec()
        }

    def get_planned_premium_houses_num(self):
        return int(self.PLANNED_HOUSES_NUM * self.PLANNED_PREMIUM_RATIO)
    
    def get_planned_standard_houses_num(self):
        return self.PLANNED_HOUSES_NUM - self.get_planned_premium_houses_num()


@dataclass
class HouseTestMeta():
    entry_timing: int
    time_inside: int

class HouseBuildResult(Enum):
    NOT_ENOUGH_RESOURCES = 1
    SUCCESSFUL = 2
    BROKEN_PARTS = 3

class HouseVerdict(Enum):
    SUITABLE_FOR_SALE = 1
    UTILIZATION = 2

class VerdictReason(Enum):
    NO_ENTRY = 1
    LATE_ENTRY = 2
    QUICK_LEAVE = 3
    ALL_TESTS_PASSED = 4

@dataclass
class HouseTestResult():
    meta: HouseTestMeta
    verdict: HouseVerdict
    reason: VerdictReason

# =============== #
#    СИМУЛЯЦИЯ    #
# =============== #

class CatHouseFactory:
    def __init__(self, env: simpy.Environment, config: CatFactoryConfig, rng: CustomRNG, logging_on=False):
        self.env = env
        self.rng = rng
        self.config = config
        self.logging_on = logging_on

        self.stats = []

    def run(self, *args, **kwargs):
        # Запуск процессов
        self.env.process(self.orchestrate())
        self.init()
        self.env.run(*args, **kwargs)

        self.stats.append(self.current_stats)

    def init(self):
        self.current_stats = {
            "execution_times_by_phase": dict(),
            "house_testing_metas": [],
            "planned_houses_num": self.config.PLANNED_HOUSES_NUM
        }
        self.raw_wood_planks = SortedList(key=lambda p: p.quality)
        self.raw_fabric_rolls = SortedList(key=lambda r: r.quality)
        self.paint_stock = SortedList(key=lambda r: r.quality)

        self.wooden_parts_store = {t: SortedList(key=lambda p: p.quality) for t in set(WoodenPartType)}
        self.fabric_parts_store = {t: SortedList(key=lambda p: p.quality) for t in set(FabricPartType)}

        self.builders = simpy.Resource(self.env, self.config.BUILDERS_NUM)
        self.cats = simpy.Resource(self.env, self.config.CATS_NUM)

        self.house_build_tasks = {
            CatHouseType.STANDARD: 0,
            CatHouseType.PREMIUM: 0
        }        

        self.built_houses = {
            CatHouseType.STANDARD: [],
            CatHouseType.PREMIUM: []
        } 

        self.houses_to_test = []
        self.house_test_results = {
            HouseVerdict.SUITABLE_FOR_SALE: [],
            HouseVerdict.UTILIZATION: []
        }
        
    def log(self, message):
        if self.logging_on:
            print(f"{self.env.now}|{message}")

    def get_stats(self):
        return self.stats


    def orchestrate(self):
        start_time = self.env.now

        yield from self.materials_supply_phase()
        yield from self.manufacturing_parts_phase()
        yield from self.assembling_houses_phase()
        yield from self.testing_houses_phase()
        
        total_execution_time = self.env.now - start_time
        self.current_stats["total_execution_time"] = total_execution_time

    def materials_supply_phase(self):
        self.log(f"Начинается фаза поставки сырья")
        phase_start = self.env.now
        yield self.env.process(self.material_delivery())
        self.log(f"Завершена фаза поставки сырья")
        execution_time = self.env.now - phase_start
        self.current_stats["execution_times_by_phase"]["materials_supply_phase"] = execution_time

    def manufacturing_parts_phase(self):
        self.log(f"Начинается фаза производства деталей")
        phase_start = self.env.now
        # проработка премиум деталей
        yield simpy.AllOf(
            self.env,
            [
                self.env.process(self.part_processing(set(WoodenPartType), CatHouseType.PREMIUM)),
                self.env.process(self.part_processing(set(FabricPartType), CatHouseType.PREMIUM))
            ])

        # проработка обычных деталей
        yield simpy.AllOf(
            self.env,
            [
                self.env.process(self.part_processing(set(WoodenPartType), CatHouseType.STANDARD)),
                self.env.process(self.part_processing(set(FabricPartType), CatHouseType.STANDARD))
            ])
        execution_time = self.env.now - phase_start
        self.current_stats["execution_times_by_phase"]["manufacturing_parts_phase"] = execution_time
        
        self.log(f"Завершена фаза производства деталей")
        self.log(f"Состояние:")
        self.log(f"{len(self.raw_wood_planks)} планок дерева")
        self.log(f"{len(self.raw_fabric_rolls)} рулонов ткани")
        self.log(f"{len(self.paint_stock)} ведер краски")
        self.log(f"{sum(len(parts) for parts in self.wooden_parts_store.values())} деревянных деталей")
        self.log(f"{sum(len(parts) for parts in self.fabric_parts_store.values())} тканевых деталей")

    def assembling_houses_phase(self):
        self.log(f"Начинается фаза сборки домиков")
        start_time = self.env.now

        self.log(f"Начинается сборка премиум домиков")
        yield self.env.process(self.build_houses(CatHouseType.PREMIUM))
        self.log(f"Cборка премиум домиков завершена")

        self.log(f"Начинается сборка стандартных домиков")
        yield self.env.process(self.build_houses(CatHouseType.STANDARD))
        self.log(f"Cборка стандартных домиков завершена")
        
        execution_time = self.env.now - start_time
        self.current_stats["execution_times_by_phase"]["assembling_houses_phase"] = execution_time

        self.log(f"Завершена фаза сборки домиков")
        
        self.log(f"Состояние:")
        self.log(f"{sum(len(parts) for parts in self.wooden_parts_store.values())} деревянных деталей")
        self.log(f"{sum(len(parts) for parts in self.fabric_parts_store.values())} тканевых деталей")
        self.log(f"{len(self.built_houses[CatHouseType.PREMIUM])} премиум домиков")
        self.log(f"{len(self.built_houses[CatHouseType.STANDARD])} стандартных домиков")

        
    def testing_houses_phase(self):
        self.log(f"Начинается фаза тестирования домиков")
        start_time = self.env.now
        
        yield self.env.process(self.test_houses())
        
        execution_time = self.env.now - start_time
        self.current_stats["execution_times_by_phase"]["testing_houses_phase"] = execution_time

        self.log(f"Завершена фаза тестирования домиков")

        self.log(f"Состояние:")
        self.log(f"{len(self.houses_to_test)} непротестированных домиков")
        self.log(f"{sum(len(results) for results in self.house_test_results.values())} всего протестировано домиков")
        self.log(f"{len(self.house_test_results[HouseVerdict.UTILIZATION])} к утилизации")
        self.log(f"{len(self.house_test_results[HouseVerdict.SUITABLE_FOR_SALE])} к продаже")

        self.current_stats["for_utilization"] = len(self.house_test_results[HouseVerdict.UTILIZATION])
        self.current_stats["for_sale"] = len(self.house_test_results[HouseVerdict.SUITABLE_FOR_SALE])
        


    def material_delivery(self):
        self.log(f"Начата закупка сырья")

        # расчет необходимых материалов
        rng_config = self.config.RNG_CONFIG
        premium_houses_num = self.config.get_planned_premium_houses_num()
        standard_houses_num = self.config.get_planned_standard_houses_num()
        self.log(f"Запланировано {premium_houses_num} премиум и {standard_houses_num} стандартных домиков")
        
        house_types = set(CatHouseType)
        house_specs = self.config.HOUSE_SPECS
        planned_houses_nums = self.config.PLANNED_HOUSES_NUMS

        wood_costs = {
            house_type: house_specs[house_type].get_wood_cost() * planned_houses_nums[house_type]
            for house_type in house_types
        }

        fabric_costs = {
            house_type: house_specs[house_type].get_fabric_cost() * planned_houses_nums[house_type]
            for house_type in house_types
        }

        paint_costs = {
            house_type: house_specs[house_type].get_paint_cost() * planned_houses_nums[house_type]
            for house_type in house_types
        }

        execution_time = int(self.rng.normal(
            mu=rng_config["material_delivery_time"]["mu"],
            sigma=rng_config["material_delivery_time"]["sigma"]))        
        
        yield self.env.timeout(execution_time)

        raw_wood_batch = [
            RawWoodPlank(
                quality=self.rng.normal(
                    mu=rng_config["raw_material_quality"][house_type]["mu"],
                    sigma=rng_config["raw_material_quality"][house_type]["sigma"] 
                )
            ) for house_type, cost in wood_costs.items() for _ in range(cost)
        ]

        raw_fabric_batch = [
            RawFabricRoll(
                quality=self.rng.normal(
                    mu=rng_config["raw_material_quality"][house_type]["mu"],
                    sigma=rng_config["raw_material_quality"][house_type]["sigma"] 
                )
            ) for house_type, cost in fabric_costs.items() for _ in range(cost)
        ]

        paint_batch = [
            PaintBucket(
                quality=self.rng.normal(
                    mu=rng_config["raw_material_quality"][house_type]["mu"],
                    sigma=rng_config["raw_material_quality"][house_type]["sigma"] 
                ),
                color=self.rng.choice(list(Color))
            ) for house_type, cost in paint_costs.items() for _ in range(cost)
        ]

        # доставка материалов
        for plank in raw_wood_batch:
            self.raw_wood_planks.add(plank)

        for roll in raw_fabric_batch:
            self.raw_fabric_rolls.add(roll)

        for bucket in paint_batch:
            self.paint_stock.add(bucket)
        
        self.log(f"Закупка сырья завершена")
        self.log(f"Поставка материалов | "
                f"Дерево: {len(raw_wood_batch)}ед, "
                f"Ткань: {len(raw_fabric_batch)}ед, "
                f"Краска: {len(paint_batch)}ед")


    def part_processing(self, part_types, house_type: CatHouseType):
        self.log(f"начало изготовления деталей типов {part_types} для дома типа {house_type}")
        
        house_spec = self.config.HOUSE_SPECS[house_type] 
        planned_houses_num = self.config.PLANNED_HOUSES_NUMS[house_type]
        parts_to_make = house_spec.get_parts_by_types(part_types) * planned_houses_num

        parts_planned = len(parts_to_make)
        parts_completed = 0

        self.log(f"Изготавливаем {parts_planned} деталей")
        for i, part_type in enumerate(parts_to_make):
            # self.log(f"Делаем {i} премиум деталь")
            while self.has_mats_for_part(part_type, house_type):
                result_event = yield self.env.process(self.make_part(part_type))
                if result_event.value:  # если получилось, переходим к следующей
                    parts_completed += 1
                    break

        self.log(f"конец изготовления деталей типов {part_types} для дома типа {house_type}")
        self.log(f"Всего изготовлено деталей {parts_completed} из {parts_planned}")


    def has_mats_for_part(self, part_type, house_type):
        is_premium = house_type in {CatHouseType.PREMIUM}
        if part_type in set(WoodenPartType):
            return (len(self.raw_wood_planks) > 0 
                and (not is_premium or self.raw_wood_planks[-1].quality > self.config.MIN_PREMIUM_WOOD_QUALITY) 
                and len(self.paint_stock) > 0 
                and (not is_premium or self.paint_stock[-1].quality > self.config.MIN_PREMIUM_PAINT_QUALITY))
        if part_type in set(FabricPartType):
            return (len(self.raw_fabric_rolls) > 0 
                and (not is_premium or self.raw_fabric_rolls[-1].quality > self.config.MIN_PREMIUM_FABRIC_QUALITY) 
                and len(self.paint_stock) > 0 
                and (not is_premium or self.paint_stock[-1].quality > self.config.MIN_PREMIUM_PAINT_QUALITY))
        raise Exception(f"unrecognized part_type: {part_type}")

    def make_part(self, part_type):
        if part_type in set(WoodenPartType):
            return self.make_wooden_part(part_type)
        if part_type in set(FabricPartType):
            return self.make_fabric_part(part_type)
        raise Exception(f"unrecognized part_type: {part_type}")
    
        
    def make_fabric_part(self, part_type: FabricPartType):
        plank: RawFabricRoll = self.raw_fabric_rolls.pop()
        paint_bucket: PaintBucket = self.paint_stock.pop()
        rng_config = self.config.RNG_CONFIG

        execution_time = int(self.rng.truncated_normal(
            mu=rng_config["fabric_processing_time"]["mu"],
            sigma=rng_config["fabric_processing_time"]["sigma"],
            a=rng_config["fabric_processing_time"]["min_time"],
            b=rng_config["fabric_processing_time"]["max_time"],
            ))        
        yield self.env.timeout(execution_time)
        
        # break logic
        if (self.rng.uniform(0.0, 1.0) < self.config.BROKEN_ROLLS_RATIO):
            self.log(f"Сломалась деталь {part_type}")
            return self.env.event().succeed(False)  

        process_quality = random.uniform(0.7, 0.9) # TODO: randomize
        quality = math.prod([plank.quality, paint_bucket.quality, process_quality]) ** (1 / 3)
        part = FabricHousePart(
            quality=quality, 
            color=paint_bucket.color, 
            type=part_type)
        self.fabric_parts_store[part_type].add(part)

        return self.env.event().succeed(True)
    
    def make_wooden_part(self, part_type: WoodenPartType):
        plank: RawWoodPlank = self.raw_wood_planks.pop()
        paint_bucket: PaintBucket = self.paint_stock.pop()
        rng_config = self.config.RNG_CONFIG

        execution_time = int(self.rng.truncated_normal(
            mu=rng_config["wooden_processing_time"]["mu"],
            sigma=rng_config["wooden_processing_time"]["sigma"],
            a=rng_config["wooden_processing_time"]["min_time"],
            b=rng_config["wooden_processing_time"]["max_time"]
            ))        
        yield self.env.timeout(execution_time)
        
        # break logic 
        if (self.rng.uniform(0.0, 1.0) < self.config.BROKEN_PLANKS_RATIO):
            self.log(f"Сломалась деталь {part_type}")
            return self.env.event().succeed(False)  


        process_quality = random.uniform(0.7, 0.9) # TODO: randomize
        quality = math.prod([plank.quality, paint_bucket.quality, process_quality]) ** (1 / 3)
        part = WoodenHousePart(
            quality=quality, 
            color=paint_bucket.color, 
            type=part_type)
        self.wooden_parts_store[part_type].add(part)

        return self.env.event().succeed(True)
            


    def build_houses(self, house_type: CatHouseType):
        self.house_build_tasks[house_type] = self.config.PLANNED_HOUSES_NUMS[house_type]
        builders_jobs = [self.env.process(self.builder_job(house_type)) for _ in range(self.builders.capacity)]
        yield simpy.AllOf(self.env, builders_jobs)

        

    def builder_job(self, house_type):
        self.log(f"Начата смена сборщика, ждем освобождения")
        with self.builders.request() as builder_request:
            yield builder_request
            self.log(f"Сборщик приступил к работе")
            while self.house_build_tasks[house_type] > 0:
                self.house_build_tasks[house_type] -= 1
                house_build_result = yield self.env.process(self.build_house(house_type))
                if house_build_result.value == HouseBuildResult.SUCCESSFUL:
                    continue
                elif house_build_result.value == HouseBuildResult.BROKEN_PARTS:
                    self.house_build_tasks[house_type] += 1
                elif house_build_result.value == HouseBuildResult.NOT_ENOUGH_RESOURCES:
                    self.house_build_tasks[house_type] = 0
                    break
            self.log(f"Смена сборщика завершена, задач на домик {house_type} больше нет")

    def build_house(self, house_type: CatHouseType):
        rng_config = self.config.RNG_CONFIG
        house_spec = self.config.HOUSE_SPECS[house_type]
        part_types_to_get = house_spec.get_parts()

        retrieved_parts = []
        for part_type in part_types_to_get:
            if self.has_house_part(part_type, house_type):
                retrieved_parts.append(self.get_house_part(part_type))
            else:
                self.return_parts(retrieved_parts)
                return self.env.event().succeed(HouseBuildResult.NOT_ENOUGH_RESOURCES)

        yield self.env.timeout(random.randint(10, 20))

        used_parts = [(part, self.rng.uniform(0.0, 1.0) < self.config.BROKEN_PARTS_RATIO) for part in retrieved_parts]
        unbroken_parts = [part for part, is_broken in used_parts if not is_broken]
        if len(unbroken_parts) < len(used_parts):
            self.return_parts(unbroken_parts)
            return self.env.event().succeed(HouseBuildResult.BROKEN_PARTS)
        
        if house_type == CatHouseType.PREMIUM:
            build_quality = self.rng.normal(
                mu=rng_config["house_build_quality"][CatHouseType.PREMIUM]["mu"],
                sigma=rng_config["house_build_quality"][CatHouseType.PREMIUM]["sigma"]
            )
            self.built_houses[house_type].append(
                PremiumCatHouse(
                    build_quality=build_quality,
                    parts=unbroken_parts
                )
            )
        elif house_type == CatHouseType.STANDARD:
            build_quality = self.rng.normal(
                mu=rng_config["house_build_quality"][CatHouseType.STANDARD]["mu"],
                sigma=rng_config["house_build_quality"][CatHouseType.STANDARD]["sigma"]
            )
            self.built_houses[house_type].append(
                StandardCatHouse(
                    build_quality=build_quality,
                    parts=unbroken_parts
                )
            )
        return self.env.event().succeed(HouseBuildResult.SUCCESSFUL)
        
    def return_parts(self, parts: List[CatHousePart]):
        for part in parts:
            if isinstance(part, WoodenHousePart):
                self.wooden_parts_store[part.get_type()].add(part)
            elif isinstance(part, FabricHousePart):
                self.fabric_parts_store[part.get_type()].add(part)
    
    def has_house_part(self, part_type: Union[WoodenPartType, FabricPartType], house_type: CatHouseType):
        if isinstance(part_type, WoodenPartType):
            return (
                len(self.wooden_parts_store[part_type]) > 0
                and (
                    house_type == CatHouseType.STANDARD 
                    or self.wooden_parts_store[part_type][-1].quality > self.config.MIN_PREMIUM_WOODEN_PART_QUALITY
                )
            )
        elif isinstance(part_type, FabricPartType):
            return (
                len(self.fabric_parts_store[part_type]) > 0
                and (
                    house_type == CatHouseType.STANDARD 
                    or self.fabric_parts_store[part_type][-1].quality > self.config.MIN_PREMIUM_FABRIC_PART_QUALITY
                )
            )
        
    def get_house_part(self, part_type: Union[WoodenPartType, FabricPartType]):
        if isinstance(part_type, WoodenPartType):
            return self.wooden_parts_store[part_type].pop()
        if isinstance(part_type, FabricPartType):
            return self.fabric_parts_store[part_type].pop()
        
    
    def test_houses(self):
        self.houses_to_test = [house for house_type in set(CatHouseType) for house in self.built_houses[house_type]]
        cats_jobs = [self.env.process(self.cat_job()) for _ in range(self.cats.capacity)]
        yield simpy.AllOf(self.env, cats_jobs)

    def cat_job(self):
        self.log(f"Начата смена котика, ждем приступления")
        with self.cats.request() as cat_request:
            yield cat_request
            self.log(f"Котик приступил к работе")
            while len(self.houses_to_test) > 0:
                yield self.env.process(self.test_house())
            self.log(f"Смена котика завершена, задач тестирование домиков больше нет")

    def test_house(self):
        rng_config = self.config.RNG_CONFIG
        house: CatHouse = self.houses_to_test.pop()
        max_test_time = self.config.MAX_TEST_TIME

        qualities = [part.quality for part in house.parts] + [house.build_quality]
        overall_quality = math.prod(qualities) ** (1/len(qualities))
        
        base_scale = rng_config["entry_timing"]["scale"]
        base_multiplier = rng_config["entry_timing"]["base_multiplier"]
        scale = base_scale / (base_multiplier - overall_quality)
        entry_timing = min(max(int(self.rng.exponential(scale=scale)), 0), max_test_time)
        entry_timing = entry_timing if entry_timing <= self.config.MAX_ENTRY_TIME else None 

        base_mu = rng_config["time_inside"]["base_mu"]
        sigma = rng_config["time_inside"]["sigma"]
        time_inside = min(max(
            int(self.rng.normal(
            mu=base_mu * overall_quality, 
            sigma=sigma)
            ), 0), max_test_time)
        time_inside = None if entry_timing is None else min(time_inside, max_test_time - entry_timing)

        yield self.env.timeout(max_test_time if entry_timing is None else entry_timing + time_inside)
        
        house_test_meta = HouseTestMeta(
            entry_timing=entry_timing,
            time_inside=time_inside
        )
        house_test_result = self.make_test_result(house_test_meta)
        self.house_test_results[house_test_result.verdict].append(house)

        self.current_stats["house_testing_metas"].append({
            "entry_timing": entry_timing,
            "time_inside": time_inside
        })

        return self.env.event().succeed()        

    def make_test_result(self, meta: HouseTestMeta):
        if meta.entry_timing is None:
            return HouseTestResult(
                meta=meta,
                verdict=HouseVerdict.UTILIZATION,
                reason=VerdictReason.NO_ENTRY
            )
        if meta.entry_timing > self.config.MAX_ENTRY_TIME:
            return HouseTestResult(
                meta=meta,
                verdict=HouseVerdict.UTILIZATION,
                reason=VerdictReason.LATE_ENTRY
            )
        if meta.time_inside < self.config.MIN_TIME_INSIDE:
            return HouseTestResult(
                meta=meta,
                verdict=HouseVerdict.UTILIZATION,
                reason=VerdictReason.QUICK_LEAVE
            )
        return HouseTestResult(
            meta=meta,
            verdict=HouseVerdict.SUITABLE_FOR_SALE,
            reason=VerdictReason.ALL_TESTS_PASSED
        )

        