"""Frente 3 — los cinco analizadores, cada uno contra un caso conocido.

Escritas ANTES de la implementacion: este archivo define la interfaz y el
comportamiento esperado, y la implementacion se escribe hasta que pasen.

Ninguna prueba toca MariaDB, MinIO ni la red. Los analizadores son funciones
puras sobre un `CocoDataset`; el unico que necesita disco es el de duplicados,
y usa imagenes que se generan en un `tmp_path`.
"""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from dataset_quality.analyzers import (
    analyze_class_imbalance,
    analyze_degenerate_boxes,
    analyze_duplicates,
    analyze_small_objects,
    analyze_spatial_bias,
    describe,
    run_all,
)
from dataset_quality.models.coco import CocoDataset
from dataset_quality.models.quality import (
    ClassImbalanceCheck,
    DegenerateBoxesCheck,
    DuplicatesCheck,
    MinImagesPerClassCheck,
    QualityConfig,
    SmallObjectsCheck,
    SpatialBiasCheck,
    SplitsConfig,
)
from dataset_quality.models.splits import SplitRatios


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def coco(
    images: list[tuple[int, str, int, int]],
    boxes: list[tuple[int, int, int, float, float, float, float]],
    categories: list[tuple[int, str]],
) -> CocoDataset:
    """Construye un COCO valido desde tuplas. El area se deriva de la bbox.

    images: (id, file_name, width, height)
    boxes:  (id, image_id, category_id, x, y, w, h)
    """
    return CocoDataset.model_validate(
        {
            "images": [{"id": i, "file_name": n, "width": w, "height": h} for i, n, w, h in images],
            "annotations": [
                {
                    "id": bid,
                    "image_id": img,
                    "category_id": cat,
                    "bbox": [x, y, w, h],
                    "area": w * h,
                    "iscrowd": 0,
                }
                for bid, img, cat, x, y, w, h in boxes
            ],
            "categories": [{"id": i, "name": n} for i, n in categories],
        }
    )


def draw(path, seed: int, size: tuple[int, int] = (256, 192)) -> None:
    """Imagen con estructura reconocible: el pHash necesita algo que mirar.

    Una imagen de color plano tiene pHash identico a cualquier otra plana,
    porque no hay frecuencias que comparar.
    """
    canvas = Image.new("RGB", size, (240, 240, 245))
    painter = ImageDraw.Draw(canvas)
    for index in range(7):
        offset = (index * 31 + seed * 47) % (size[0] - 60)
        painter.rectangle(
            [offset, 15 + index * 22, offset + 52, 58 + index * 22],
            fill=(30 + index * 28, (90 + seed * 40) % 256, 210 - index * 24),
        )
    canvas.save(path, "JPEG", quality=93)


@pytest.fixture
def photos(tmp_path):
    """Genera imagenes en disco y devuelve el directorio."""

    def build(**named_seeds: int):
        for name, seed in named_seeds.items():
            draw(tmp_path / f"{name}.jpg", seed)
        return tmp_path

    return build


# --------------------------------------------------------------------------
# Objetos pequenos — area RELATIVA a la imagen, no 32x32 absolutos
# --------------------------------------------------------------------------
SMALL = SmallObjectsCheck(area_ratio_threshold=0.01, max_ratio=0.30)


def test_objeto_bajo_el_umbral_relativo_se_marca() -> None:
    # Imagen 100x100 = 10.000 px2. Caja 5x10 = 50 px2 -> 0.005 < 0.01
    dataset = coco(
        images=[(1, "a.jpg", 100, 100)],
        boxes=[(1, 1, 1, 0, 0, 5, 10)],
        categories=[(1, "car")],
    )
    result = analyze_small_objects(dataset, SMALL)

    assert result.offenders == [1]
    assert result.observed == pytest.approx(1.0)


def test_objeto_grande_no_se_marca() -> None:
    # Caja 40x40 = 1.600 px2 sobre 10.000 -> 0.16, muy por encima de 0.01
    dataset = coco(
        images=[(1, "a.jpg", 100, 100)],
        boxes=[(1, 1, 1, 0, 0, 40, 40)],
        categories=[(1, "car")],
    )
    result = analyze_small_objects(dataset, SMALL)

    assert result.offenders == []
    assert result.observed == pytest.approx(0.0)


def test_objeto_justo_en_el_umbral_no_se_marca() -> None:
    """El umbral es inclusivo: exactamente 0.01 esta permitido."""
    # 10x10 = 100 px2 sobre 10.000 -> exactamente 0.01
    dataset = coco(
        images=[(1, "a.jpg", 100, 100)],
        boxes=[(1, 1, 1, 0, 0, 10, 10)],
        categories=[(1, "car")],
    )
    assert analyze_small_objects(dataset, SMALL).offenders == []


def test_objetos_pequenos_falla_al_pasar_el_maximo() -> None:
    # 3 de 4 cajas son diminutas -> 0.75 > max_ratio 0.30
    dataset = coco(
        images=[(1, "a.jpg", 100, 100)],
        boxes=[
            (1, 1, 1, 0, 0, 5, 5),
            (2, 1, 1, 10, 10, 5, 5),
            (3, 1, 1, 20, 20, 5, 5),
            (4, 1, 1, 30, 30, 40, 40),
        ],
        categories=[(1, "car")],
    )
    result = analyze_small_objects(dataset, SMALL)

    assert result.observed == pytest.approx(0.75)
    assert result.status == "fail"
    assert result.severity == "warning"


def test_el_umbral_es_relativo_al_tamano_de_cada_imagen() -> None:
    """La misma caja es pequena en una foto grande y normal en una chica."""
    dataset = coco(
        images=[(1, "grande.jpg", 1000, 1000), (2, "chica.jpg", 100, 100)],
        boxes=[(1, 1, 1, 0, 0, 20, 20), (2, 2, 1, 0, 0, 20, 20)],
        categories=[(1, "car")],
    )
    # 400/1.000.000 = 0.0004 (pequena) vs 400/10.000 = 0.04 (normal)
    assert analyze_small_objects(dataset, SMALL).offenders == [1]


def test_analizador_desactivado_se_salta() -> None:
    dataset = coco([(1, "a.jpg", 100, 100)], [(1, 1, 1, 0, 0, 5, 5)], [(1, "car")])
    disabled = SmallObjectsCheck(enabled=False, area_ratio_threshold=0.01, max_ratio=0.30)

    assert analyze_small_objects(dataset, disabled).status == "skipped"


def test_dataset_sin_cajas_no_divide_entre_cero() -> None:
    dataset = coco([(1, "a.jpg", 100, 100)], [], [(1, "car")])
    result = analyze_small_objects(dataset, SMALL)

    assert result.observed == 0.0
    assert result.status == "pass"


# --------------------------------------------------------------------------
# Desbalance de clases — se cuentan IMAGENES, no cajas
# --------------------------------------------------------------------------
BALANCE = ClassImbalanceCheck(max_ratio_max_min=2.0)


def test_desbalance_es_la_razon_entre_la_clase_mayor_y_la_menor() -> None:
    dataset = coco(
        images=[(1, "a.jpg", 100, 100), (2, "b.jpg", 100, 100), (3, "c.jpg", 100, 100)],
        boxes=[
            (1, 1, 1, 0, 0, 10, 10),
            (2, 2, 1, 0, 0, 10, 10),
            (3, 3, 1, 0, 0, 10, 10),
            (4, 1, 2, 20, 20, 10, 10),
        ],
        categories=[(1, "car"), (2, "cat")],
    )
    result = analyze_class_imbalance(dataset, BALANCE)

    assert result.observed == pytest.approx(3.0)  # car 3 imagenes / cat 1
    assert result.status == "fail"


def test_desbalance_cuenta_imagenes_distintas_no_cajas() -> None:
    """Una foto con siete coches aporta UNA imagen a `car`, no siete."""
    dataset = coco(
        images=[(1, "a.jpg", 100, 100), (2, "b.jpg", 100, 100)],
        boxes=[
            (1, 1, 1, 0, 0, 10, 10),
            (2, 1, 1, 20, 0, 10, 10),
            (3, 1, 1, 40, 0, 10, 10),
            (4, 2, 2, 0, 0, 10, 10),
        ],
        categories=[(1, "car"), (2, "cat")],
    )
    # Si contara cajas seria 3.0; contando imagenes es 1.0.
    assert analyze_class_imbalance(dataset, BALANCE).observed == pytest.approx(1.0)


def test_dataset_balanceado_pasa() -> None:
    dataset = coco(
        images=[(1, "a.jpg", 100, 100), (2, "b.jpg", 100, 100)],
        boxes=[(1, 1, 1, 0, 0, 10, 10), (2, 2, 2, 0, 0, 10, 10)],
        categories=[(1, "car"), (2, "cat")],
    )
    result = analyze_class_imbalance(dataset, BALANCE)

    assert result.observed == pytest.approx(1.0)
    assert result.status == "pass"


def test_desbalance_senala_las_clases_infrarrepresentadas() -> None:
    dataset = coco(
        images=[(i, f"{i}.jpg", 100, 100) for i in range(1, 6)],
        boxes=[(i, i, 1, 0, 0, 10, 10) for i in range(1, 5)] + [(5, 5, 2, 0, 0, 10, 10)],
        categories=[(1, "car"), (2, "cat")],
    )
    # car 4 / cat 1 = 4.0 > 2.0
    assert analyze_class_imbalance(dataset, BALANCE).offenders == [2]


def test_una_sola_clase_no_esta_desbalanceada() -> None:
    dataset = coco([(1, "a.jpg", 100, 100)], [(1, 1, 1, 0, 0, 10, 10)], [(1, "car")])
    result = analyze_class_imbalance(dataset, BALANCE)

    assert result.observed == pytest.approx(1.0)
    assert result.status == "pass"


def test_una_clase_sin_ninguna_imagen_no_hace_infinito_el_ratio() -> None:
    """Una categoria declarada pero nunca usada es un caso aparte, no un 1/0."""
    dataset = coco(
        images=[(1, "a.jpg", 100, 100)],
        boxes=[(1, 1, 1, 0, 0, 10, 10)],
        categories=[(1, "car"), (2, "jamas_usada")],
    )
    result = analyze_class_imbalance(dataset, BALANCE)

    assert result.observed != float("inf")
    assert 2 in result.offenders


# --------------------------------------------------------------------------
# Cajas degeneradas — las que se salen de la imagen
# --------------------------------------------------------------------------
DEGENERATE = DegenerateBoxesCheck(max_ratio=0.0)


def test_caja_que_se_sale_de_la_imagen_se_marca() -> None:
    dataset = coco(
        images=[(1, "a.jpg", 100, 100)],
        boxes=[(1, 1, 1, 90, 90, 40, 40)],  # llega a 130 > 100
        categories=[(1, "car")],
    )
    result = analyze_degenerate_boxes(dataset, DEGENERATE)

    assert result.offenders == [1]
    assert result.status == "fail"
    assert result.severity == "error"


def test_caja_pegada_al_borde_es_valida() -> None:
    """Tocar el borde exacto no es salirse."""
    dataset = coco(
        images=[(1, "a.jpg", 100, 100)],
        boxes=[(1, 1, 1, 60, 60, 40, 40)],  # llega justo a 100
        categories=[(1, "car")],
    )
    result = analyze_degenerate_boxes(dataset, DEGENERATE)

    assert result.offenders == []
    assert result.status == "pass"


def test_cajas_degeneradas_reporta_la_proporcion() -> None:
    dataset = coco(
        images=[(1, "a.jpg", 100, 100)],
        boxes=[(1, 1, 1, 90, 90, 40, 40), (2, 1, 1, 0, 0, 10, 10)],
        categories=[(1, "car")],
    )
    assert analyze_degenerate_boxes(dataset, DEGENERATE).observed == pytest.approx(0.5)


# --------------------------------------------------------------------------
# Sesgo espacial
# --------------------------------------------------------------------------
SPATIAL = SpatialBiasCheck(grid_size=4, max_cell_share=0.25)


def test_todos_los_objetos_en_una_celda_es_sesgo_total() -> None:
    dataset = coco(
        images=[(1, "a.jpg", 400, 400)],
        boxes=[(i, 1, 1, 10, 10, 20, 20) for i in range(1, 6)],
        categories=[(1, "car")],
    )
    result = analyze_spatial_bias(dataset, SPATIAL)

    assert result.observed == pytest.approx(1.0)
    assert result.status == "fail"


def test_objetos_repartidos_dan_el_reparto_uniforme() -> None:
    """Un objeto en cada celda de la rejilla 4x4 -> 1/16 por celda."""
    boxes = []
    box_id = 1
    for row in range(4):
        for col in range(4):
            cx, cy = col * 100 + 50, row * 100 + 50
            boxes.append((box_id, 1, 1, cx - 5, cy - 5, 10, 10))
            box_id += 1
    dataset = coco([(1, "a.jpg", 400, 400)], boxes, [(1, "car")])
    result = analyze_spatial_bias(dataset, SPATIAL)

    assert result.observed == pytest.approx(1 / 16)
    assert result.status == "pass"


def test_sesgo_espacial_usa_el_centro_de_la_caja() -> None:
    """Una caja grande pertenece a la celda donde cae su centro."""
    dataset = coco(
        images=[(1, "a.jpg", 400, 400)],
        boxes=[(1, 1, 1, 0, 0, 390, 390)],  # centro en (195, 195) -> celda (1,1)
        categories=[(1, "car")],
    )
    assert analyze_spatial_bias(dataset, SPATIAL).observed == pytest.approx(1.0)


# --------------------------------------------------------------------------
# Duplicados por pHash
# --------------------------------------------------------------------------
DUPLICATES = DuplicatesCheck(phash_hamming_distance=6, max_ratio=0.0)


def test_copia_recomprimida_y_reescalada_se_detecta(tmp_path) -> None:
    """El caso que un md5 NO detecta y que infla el conteo por clase."""
    draw(tmp_path / "original.jpg", seed=3)
    with Image.open(tmp_path / "original.jpg") as handle:
        copia = handle.resize((180, 135), Image.Resampling.LANCZOS)
        copia = copia.resize(handle.size, Image.Resampling.LANCZOS)
    copia.save(tmp_path / "copia.jpg", "JPEG", quality=40)

    dataset = coco(
        images=[(1, "original.jpg", 256, 192), (2, "copia.jpg", 256, 192)],
        boxes=[(1, 1, 1, 0, 0, 10, 10)],
        categories=[(1, "car")],
    )
    result = analyze_duplicates(dataset, DUPLICATES, tmp_path)

    assert result.offenders == [2]
    assert result.status == "fail"


def test_imagenes_distintas_no_son_duplicados(photos) -> None:
    images_dir = photos(a=1, b=9)
    dataset = coco(
        images=[(1, "a.jpg", 256, 192), (2, "b.jpg", 256, 192)],
        boxes=[(1, 1, 1, 0, 0, 10, 10)],
        categories=[(1, "car")],
    )
    result = analyze_duplicates(dataset, DUPLICATES, images_dir)

    assert result.offenders == []
    assert result.status == "pass"


def test_la_proporcion_de_duplicados_es_sobre_el_total_de_imagenes(photos) -> None:
    images_dir = photos(a=1, b=9, c=17)
    # `d` es copia byte a byte de `a`
    (images_dir / "d.jpg").write_bytes((images_dir / "a.jpg").read_bytes())

    dataset = coco(
        images=[
            (1, "a.jpg", 256, 192),
            (2, "b.jpg", 256, 192),
            (3, "c.jpg", 256, 192),
            (4, "d.jpg", 256, 192),
        ],
        boxes=[(1, 1, 1, 0, 0, 10, 10)],
        categories=[(1, "car")],
    )
    result = analyze_duplicates(dataset, DUPLICATES, images_dir)

    assert result.offenders == [4]
    assert result.observed == pytest.approx(0.25)  # 1 de 4


def test_una_imagen_que_falta_en_disco_no_rompe_el_analisis(photos) -> None:
    images_dir = photos(a=1)
    dataset = coco(
        images=[(1, "a.jpg", 256, 192), (2, "no_descargada.jpg", 256, 192)],
        boxes=[(1, 1, 1, 0, 0, 10, 10)],
        categories=[(1, "car")],
    )
    result = analyze_duplicates(dataset, DUPLICATES, images_dir)

    assert result.status == "pass"


# --------------------------------------------------------------------------
# Descriptiva
# --------------------------------------------------------------------------
def test_la_descriptiva_resume_el_dataset() -> None:
    dataset = coco(
        images=[(1, "a.jpg", 100, 100), (2, "b.jpg", 200, 200)],
        boxes=[
            (1, 1, 1, 0, 0, 10, 10),
            (2, 1, 1, 20, 20, 10, 10),
            (3, 2, 2, 0, 0, 50, 50),
        ],
        categories=[(1, "car"), (2, "cat")],
    )
    stats = describe(dataset)

    assert stats.totals.images == 2
    assert stats.totals.annotations == 3
    assert stats.totals.categories == 2
    assert stats.images_per_class == {"car": 1, "cat": 1}
    assert stats.boxes_per_class == {"car": 2, "cat": 1}
    assert stats.annotations_per_image == pytest.approx(1.5)


def test_la_descriptiva_incluye_imagenes_sin_anotar() -> None:
    dataset = coco(
        images=[(1, "a.jpg", 100, 100), (2, "vacia.jpg", 100, 100)],
        boxes=[(1, 1, 1, 0, 0, 10, 10)],
        categories=[(1, "car")],
    )
    assert describe(dataset).images_without_annotations == 1


# --------------------------------------------------------------------------
# Orquestacion
# --------------------------------------------------------------------------
def full_config(**overrides) -> QualityConfig:
    base = {
        # El minimo real del curso; las pruebas de este frente usan datasets
        # diminutos, asi que se relaja aqui para no tapar lo que se esta midiendo.
        "min_images_per_class": MinImagesPerClassCheck(min_images=1, min_classes=1),
        "small_objects": SmallObjectsCheck(area_ratio_threshold=0.01, max_ratio=0.5),
        "class_imbalance": ClassImbalanceCheck(max_ratio_max_min=10.0),
        "duplicates": DuplicatesCheck(phash_hamming_distance=6, max_ratio=0.1),
        "degenerate_boxes": DegenerateBoxesCheck(max_ratio=0.0),
        "spatial_bias": SpatialBiasCheck(grid_size=4, max_cell_share=0.9),
        "splits": SplitsConfig(ratios=SplitRatios(train=0.7, val=0.15, test=0.15)),
    }
    return QualityConfig(**{**base, **overrides})


def test_run_all_devuelve_un_resultado_por_analizador(photos) -> None:
    images_dir = photos(a=1)
    dataset = coco([(1, "a.jpg", 256, 192)], [(1, 1, 1, 0, 0, 30, 30)], [(1, "car")])

    results = run_all(dataset, full_config(), images_dir)

    assert [r.name for r in results] == [
        "min_images_per_class",
        "small_objects",
        "class_imbalance",
        "duplicates",
        "degenerate_boxes",
        "spatial_bias",
    ]


def test_run_all_marca_como_skipped_los_desactivados(photos) -> None:
    images_dir = photos(a=1)
    dataset = coco([(1, "a.jpg", 256, 192)], [(1, 1, 1, 0, 0, 30, 30)], [(1, "car")])
    config = full_config(
        duplicates=DuplicatesCheck(enabled=False, phash_hamming_distance=6, max_ratio=0.1)
    )

    results = {r.name: r for r in run_all(dataset, config, images_dir)}

    assert results["duplicates"].status == "skipped"
    assert results["small_objects"].status != "skipped"


def test_cada_resultado_cumple_el_contrato_congelado(photos) -> None:
    """`CheckResult` es lo que consumen los Frentes 4, 7 y 8."""
    images_dir = photos(a=1)
    dataset = coco([(1, "a.jpg", 256, 192)], [(1, 1, 1, 0, 0, 30, 30)], [(1, "car")])

    for result in run_all(dataset, full_config(), images_dir):
        assert result.status in {"pass", "fail", "skipped"}
        assert result.severity in {"error", "warning"}
        assert isinstance(result.observed, float)
        assert isinstance(result.threshold, float)
        assert result.message, "cada check debe explicarse en una linea"
        assert all(isinstance(offender, int) for offender in result.offenders)
