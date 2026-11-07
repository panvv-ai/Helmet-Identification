from __future__ import annotations

import pytest

from helmet_workbench.domain.models import (
    DetectionBox,
    HelmetState,
    InvalidEmployeeNumber,
    associateFaceHelmet,
    normalizeEmployeeName,
    normalizeEmployeeNumber,
)


def testEmployeeNumberRejectsPathCharacters() -> None:
    with pytest.raises(InvalidEmployeeNumber):
        normalizeEmployeeNumber("../1001")


def testEmployeeNumberIsNormalized() -> None:
    assert normalizeEmployeeNumber("  a-1001 ") == "A-1001"


def testEmployeeNameCollapsesWhitespace() -> None:
    assert normalizeEmployeeName("  张   三  ") == "张 三"


def testFaceInsideNoHelmetPersonIsClassifiedAsWithoutHelmet() -> None:
    face = DetectionBox(120, 70, 70, 80)
    person = DetectionBox(80, 40, 180, 180)

    state, confidence = associateFaceHelmet(face, [], [person])

    assert state is HelmetState.WITHOUT_HELMET
    assert confidence > 0.9


def testClosestHelmetIsUsedWhenMultipleObjectsExist() -> None:
    face = DetectionBox(205, 105, 42, 48)
    near_hat = DetectionBox(190, 80, 70, 60)
    far_hat = DetectionBox(20, 20, 45, 45)

    state, confidence = associateFaceHelmet(face, [far_hat, near_hat], [])

    assert state is HelmetState.WITH_HELMET
    assert confidence > 0.6


def testFaceWithoutNearbyObjectsIsUnknown() -> None:
    face = DetectionBox(10, 10, 40, 40)

    assert associateFaceHelmet(face, [], []) == (HelmetState.UNKNOWN, 0.0)
