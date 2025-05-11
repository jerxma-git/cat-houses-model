from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Union
import simpy
from models import CatHousePart, CatHouseSpec, CatHouseType, PremiumCatHouse, RawWoodPlank, RawFabricRoll, PaintBucket, StandardCatHouse
from models import Color, WoodenHousePart, WoodenPartType, FabricHousePart, FabricPartType
from models import StandardHouseSpec, PremiumHouseSpec
import random
import math
from sortedcontainers import SortedList


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
            CATS_NUM = 4
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


class HouseBuildResult(Enum):
    NOT_ENOUGH_RESOURCES = 1
    SUCCESSFUL = 2
    BROKEN_PARTS = 3

# =============== #
#    СИМУЛЯЦИЯ    #
# =============== #

class CatHouseFactory:
    def __init__(self, env: simpy.Environment, config: CatFactoryConfig):
        self.env = env
        # self.raw_wood_planks = simpy.FilterStore(env, init=0)
        # self.raw_fabric_rolls = simpy.FilterStore(env, init=0)
        # self.paint_stock = simpy.FilterStore(env, init=0)

        self.raw_wood_planks = SortedList(key=lambda p: p.quality)
        self.raw_fabric_rolls = SortedList(key=lambda r: r.quality)
        self.paint_stock = SortedList(key=lambda r: r.quality)

        self.config = config
        
        # Очереди для обработанных деталей
        self.wooden_parts_store = {t: SortedList(key=lambda p: p.quality) for t in set(WoodenPartType)}
        self.fabric_parts_store = {t: SortedList(key=lambda p: p.quality) for t in set(FabricPartType)}

        self.builders = simpy.Resource(env, self.config.BUILDERS_NUM)
        self.cats = simpy.Resource(env, self.config.CATS_NUM)

        self.house_build_tasks = {
            CatHouseType.STANDARD: 0,
            CatHouseType.PREMIUM: 0
        }        

        self.built_houses = {
            CatHouseType.STANDARD: [],
            CatHouseType.PREMIUM: []
        } 
    
    def run(self, *args, **kwargs):
        # Запуск процессов
        self.env.process(self.orchestrate())
        self.env.run(*args, **kwargs)


    def orchestrate(self):
        yield self.env.process(self.material_delivery())
        
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

        print(f"{self.env.now} Завершена обработка деталей")
        print(f"Состояние:")
        print(f"{len(self.raw_wood_planks)} планок дерева")
        print(f"{len(self.raw_fabric_rolls)} рулонов ткани")
        print(f"{len(self.paint_stock)} ведер краски")
        print(f"{sum(len(parts) for parts in self.wooden_parts_store.values())} деревянных деталей")
        print(f"{sum(len(parts) for parts in self.fabric_parts_store.values())} тканевых деталей")

        print(f"{self.env.now} Начинается сборка премиум домов")
        yield self.env.process(self.build_houses(CatHouseType.PREMIUM))
        print(f"{self.env.now} Cборка премиум домов завершена")
        print(f"{self.env.now} Начинается сборка стандартных домов")
        yield self.env.process(self.build_houses(CatHouseType.STANDARD))
        print(f"{self.env.now} Cборка стандартных домов завершена")
    
        print(f"{self.env.now} Завершена обработка деталей")
        print(f"Состояние:")
        print(f"{len(self.raw_wood_planks)} планок дерева")
        print(f"{len(self.raw_fabric_rolls)} рулонов ткани")
        print(f"{len(self.paint_stock)} ведер краски")
        print(f"{sum(len(parts) for parts in self.wooden_parts_store.values())} деревянных деталей")
        print(f"{sum(len(parts) for parts in self.fabric_parts_store.values())} тканевых деталей")
        print(f"{len(self.built_houses[CatHouseType.PREMIUM])} премиум домиков")
        print(f"{len(self.built_houses[CatHouseType.STANDARD])} стандартных домиков")


        

    def material_delivery(self):
        print(f"{self.env.now}: Начата закупка сырья")

        # расчет необходимых материалов
        premium_houses_num = self.config.get_planned_premium_houses_num()
        standard_houses_num = self.config.get_planned_standard_houses_num()
        print(f"Запланировано {premium_houses_num} премиум и {standard_houses_num} стандартных домиков")
        
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

        yield self.env.timeout(15)

        raw_wood_batch = [
            RawWoodPlank(
                quality=random.uniform(0.7, 0.9)  # TODO: distribution + parametrize by housetype 
            ) for house_type, cost in wood_costs.items() for _ in range(cost)
        ]

        raw_fabric_batch = [
            RawFabricRoll(
                quality=random.uniform(0.7, 0.9)  # TODO: distribution + parametrize by housetype 
            ) for house_type, cost in fabric_costs.items() for _ in range(cost)
        ]

        paint_batch = [
            PaintBucket(
                quality=random.uniform(0.7, 0.9),  # TODO: distribution + parametrize by housetype 
                color=random.choice(list(Color))
            ) for house_type, cost in paint_costs.items() for _ in range(cost)
        ]

        # доставка материалов
        for plank in raw_wood_batch:
            self.raw_wood_planks.add(plank)

        for roll in raw_fabric_batch:
            self.raw_fabric_rolls.add(roll)

        for bucket in paint_batch:
            self.paint_stock.add(bucket)
        
        print(f"{self.env.now}: Закупка сырья завершена")
        print(f"{self.env.now}: Поставка материалов | "
                f"Дерево: {len(raw_wood_batch)}ед, "
                f"Ткань: {len(raw_fabric_batch)}ед, "
                f"Краска: {len(paint_batch)}ед")


    def part_processing(self, part_types, house_type: CatHouseType):
        print(f"{self.env.now} начало изготовления деталей типов {part_types} для дома типа {house_type}")

        house_spec = self.config.HOUSE_SPECS[house_type] 
        planned_houses_num = self.config.PLANNED_HOUSES_NUMS[house_type]
        parts_to_make = house_spec.get_parts_by_types(part_types) * planned_houses_num

        parts_planned = len(parts_to_make)
        parts_completed = 0

        print(f"Изготавливаем {parts_planned} деталей")
        for i, part_type in enumerate(parts_to_make):
            # print(f"Делаем {i} премиум деталь")
            while self.has_mats_for_part(part_type, house_type):
                result_event = yield self.env.process(self.make_part(part_type))
                if result_event.value:  # если получилось, переходим к следующей
                    parts_completed += 1
                    break

        print(f"{self.env.now} конец изготовления деталей типов {part_types} для дома типа {house_type}")
        print(f"Всего изготовлено деталей {parts_completed} из {parts_planned}")


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

        # print(f"{self.env.now} Изготавливаем деталь {part_type}")
        yield self.env.timeout(10) # TODO: rng
        
        # break logic
        if (random.uniform(0.0, 1.0) < self.config.BROKEN_ROLLS_RATIO):
            print(f"{self.env.now} Сломалась деталь {part_type}")
            return self.env.event().succeed(False)  

        process_quality = random.uniform(0.7, 0.9) # TODO: randomize
        quality = math.prod([plank.quality, paint_bucket.quality, process_quality]) ** (1 / 3)
        part = FabricHousePart(
            quality=quality, 
            color=paint_bucket.color, 
            type=part_type)
        self.fabric_parts_store[part_type].add(part)

        # print(f"{self.env.now} Готова деталь {part_type}")

        return self.env.event().succeed(True)
    
    def make_wooden_part(self, part_type: WoodenPartType):
        plank: RawWoodPlank = self.raw_wood_planks.pop()
        paint_bucket: PaintBucket = self.paint_stock.pop()

        # print(f"{self.env.now} Изготавливаем деталь {part_type}")
        yield self.env.timeout(10)
        
        # break logic 
        if (random.uniform(0.0, 1.0) < self.config.BROKEN_PLANKS_RATIO):
            print(f"{self.env.now} Сломалась деталь {part_type}")
            return self.env.event().succeed(False)  


        process_quality = random.uniform(0.7, 0.9) # TODO: randomize
        quality = math.prod([plank.quality, paint_bucket.quality, process_quality]) ** (1 / 3)
        part = WoodenHousePart(
            quality=quality, 
            color=paint_bucket.color, 
            type=part_type)
        self.wooden_parts_store[part_type].add(part)

        # print(f"{self.env.now} Готова деталь {part_type}")

        return self.env.event().succeed(True)
            


    def build_houses(self, house_type: CatHouseType):
        self.house_build_tasks[house_type] = self.config.PLANNED_HOUSES_NUMS[house_type]
        builders_jobs = [self.env.process(self.builder_job(house_type)) for _ in range(self.builders.capacity)]
        yield simpy.AllOf(self.env, builders_jobs)

        

    def builder_job(self, house_type):
        print(f"{self.env.now} Начата смена сотрудника, ждем освобождения")
        with self.builders.request() as builder_request:
            yield builder_request
            print(f"{self.env.now} Сотрудник приступил к работе")
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
            print(f"{self.env.now} Смена сотрудника завершена, задач на домик {house_type} больше нет")

    def build_house(self, house_type: CatHouseType):
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

        used_parts = [(part, random.uniform(0.0, 1.0) < self.config.BROKEN_PARTS_RATIO) for part in retrieved_parts]
        unbroken_parts = [part for part, is_broken in used_parts if not is_broken]
        if len(unbroken_parts) < len(used_parts):
            self.return_parts(unbroken_parts)
            return self.env.event().succeed(HouseBuildResult.BROKEN_PARTS)
        
        if house_type == CatHouseType.PREMIUM:
            build_quality = random.uniform(0.8, 1.0)
            self.built_houses[house_type].append(
                PremiumCatHouse(
                    build_quality=build_quality,
                    parts=unbroken_parts
                )
            )
        elif house_type == CatHouseType.STANDARD:
            build_quality = random.uniform(0.7, 0.9)
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
        
        
        

    