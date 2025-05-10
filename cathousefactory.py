from dataclasses import dataclass
import simpy
from models import CatHouseType, RawWoodPlank, RawFabricRoll, PaintBucket
from models import Color, WoodenHousePart, WoodenPartType, FabricHousePart, FabricPartType
from models import StandardHouseSpec, PremiumHouseSpec
import random
import math
from sortedcontainers import SortedList


@dataclass
class CatFactoryConfig:
    PLANNED_HOUSES_NUM = 100
    PLANNED_PREMIUM_RATIO = 0.3 

    STANDARD_HOUSE_SPEC = StandardHouseSpec()
    PREMIUM_HOUSE_SPEC = PremiumHouseSpec()

    MIN_PREMIUM_WOOD_QUALITY = 0.7
    MIN_PREMIUM_FABRIC_QUALITY = 0.7
    MIN_PREMIUM_PAINT_QUALITY = 0.7

    BROKEN_PLANKS_RATIO = 0.02

    def get_planned_premium_houses_num(self):
        return int(self.PLANNED_HOUSES_NUM * self.PLANNED_PREMIUM_RATIO)
    
    def get_planned_standard_houses_num(self):
        return self.PLANNED_HOUSES_NUM - self.get_planned_premium_houses_num()


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
        self.wooden_parts_store = SortedList(key=lambda p: p.quality)
        # self.fabric_parts_store = simpy.Store(env)
        
    
    def run(self, *args, **kwargs):
        # Запуск процессов
        self.env.process(self.orchestrate())
        self.env.run(*args, **kwargs)


    def orchestrate(self):
        yield self.env.process(self.material_delivery())
        yield self.env.process(self.wood_processing())

        print(f"Конец: {self.env.now}")
        print(f"Состояние:")
        print(f"{len(self.raw_wood_planks)} планок дерева")
        print(f"{len(self.raw_fabric_rolls)} рулонов ткани")
        print(f"{len(self.paint_stock)} ведер краски")
        print(f"{len(self.wooden_parts_store)} деревянных деталей")
    
        

    def material_delivery(self):
        print(f"{self.env.now}: Начата закупка сырья")

        # расчет необходимых материалов
        premium_houses_num = self.config.get_planned_premium_houses_num()
        standard_houses_num = self.config.get_planned_standard_houses_num()
        print(f"Запланировано {premium_houses_num} премиум и {standard_houses_num} стандартных домиков")
        
        standard_wood_cost = self.config.STANDARD_HOUSE_SPEC.get_wood_cost() * standard_houses_num
        premium_wood_cost = self.config.PREMIUM_HOUSE_SPEC.get_wood_cost() * premium_houses_num

        standard_fabric_cost = self.config.STANDARD_HOUSE_SPEC.get_fabric_cost() * standard_houses_num
        premium_fabric_cost = self.config.PREMIUM_HOUSE_SPEC.get_fabric_cost() * premium_houses_num

        standard_paint_cost = self.config.STANDARD_HOUSE_SPEC.get_paint_cost() * standard_houses_num
        premium_paint_cost = self.config.PREMIUM_HOUSE_SPEC.get_paint_cost() * premium_houses_num


        yield self.env.timeout(15)

        # TODO: randomize
        # закупка дерева
        premium_raw_wood_batch = [RawWoodPlank(
            quality=random.uniform(0.7, 0.9)) for _ in range(premium_wood_cost)] 
        standard_raw_wood_batch = [RawWoodPlank(
            quality=random.uniform(0.7, 0.9)) for _ in range(standard_wood_cost)] 
        raw_wood_batch = premium_raw_wood_batch + standard_raw_wood_batch

        # закупка ткани
        premium_raw_fabric_batch = [RawFabricRoll(
            quality=random.uniform(0.75, 0.95)) for _ in range(premium_fabric_cost)]
        standard_raw_fabric_batch = [RawFabricRoll(
            quality=random.uniform(0.75, 0.95)) for _ in range(standard_fabric_cost)]
        raw_fabric_batch = premium_raw_fabric_batch + standard_raw_fabric_batch
        
        # закупка краски
        premium_paint_batch = [PaintBucket(
            quality=random.uniform(0.7, 0.9),
            color=random.choice(list(Color))
            ) for _ in range(premium_paint_cost)] 
        standard_paint_batch = [PaintBucket(
            quality=random.uniform(0.7, 0.9),
            color=random.choice(list(Color))
            ) for _ in range(standard_paint_cost)] 
        paint_batch = premium_paint_batch + standard_paint_batch


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

    
    def wood_processing(self):
        print(f"{self.env.now} начало изготовления деревянных деталей")

        premium_parts_to_make =(
                self.config.PREMIUM_HOUSE_SPEC.get_parts_by_types(set(WoodenPartType))
                * self.config.get_planned_premium_houses_num()
        )
        standard_parts_to_make = (
                self.config.STANDARD_HOUSE_SPEC.get_parts_by_types(set(WoodenPartType))
                * self.config.get_planned_standard_houses_num()
        )
        
        parts_planned = len(premium_parts_to_make + standard_parts_to_make)
        parts_completed = 0

        print(f"Планируется изготовление следующих деталей {parts_planned}")
        print(premium_parts_to_make)
        for i, part_type in enumerate(premium_parts_to_make):
            # print(f"Делаем {i} премиум деталь")
            while self.has_mats_for_wooden_part(True):
                result_event = yield self.env.process(self.make_wooden_part(part_type))
                if result_event.value:  # если получилось, переходим к следующей
                    parts_completed += 1
                    break
            
        
        for part_type in standard_parts_to_make:
            while self.has_mats_for_wooden_part(False):
                result_event = yield self.env.process(self.make_wooden_part(part_type))
                if result_event.value:  # если получилось, переходим к следующей
                    parts_completed += 1
                    break


        print(f"{self.env.now} конец изготовления деревянных деталей")
        print(f"Всего изготовлено деталей {parts_completed} из {parts_planned}")
        print(f"Изготовленные детали: {list(self.wooden_parts_store)}")


    def has_mats_for_wooden_part(self, is_premium):
        return (len(self.raw_wood_planks) > 0 
            and (not is_premium or self.raw_wood_planks[-1].quality > self.config.MIN_PREMIUM_WOOD_QUALITY) 
            and len(self.paint_stock) > 0 
            and (not is_premium or self.paint_stock[-1].quality > self.config.MIN_PREMIUM_PAINT_QUALITY))

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
        self.wooden_parts_store.add(part)

        # print(f"{self.env.now} Готова деталь {part_type}")

        return self.env.event().succeed(True)
            


    