# -*- coding: utf-8 -*-
"""Generator diagramow BPMN 2.0 (XML + BPMN DI) z deklaratywnej specyfikacji.

Uklad liczy kod, nie czlowiek: kazdy element dostaje (pula, tor, kolumna, wiersz),
a wspolrzedne, wysokosci torow i punkty zalamania krawedzi wychodza z siatki.
Poprawka jednego zadania nie wymaga wiec przesuwania reszty diagramu.

Wynik otwiera sie w bpmn.io, Camunda Modeler i importuje do Bizagi Modeler.

Autor: Mateusz Biernat
"""
from __future__ import annotations

import html
from dataclasses import dataclass, field

COL_W = 180          # szerokosc kolumny siatki
ROW_H = 120          # wysokosc wiersza w torze
LANE_PAD = 20        # margines gorny/dolny toru
LANE_LABEL_W = 30    # pionowy pasek z nazwa toru
POOL_X = 160         # lewa krawedz puli
POOL_GAP = 60        # odstep miedzy pulami

SIZES = {
    "task": (150, 80),
    "gateway": (50, 50),
    "event": (36, 36),
}

TASK_TYPES = {
    "user": "userTask",
    "service": "serviceTask",
    "rule": "businessRuleTask",
    "send": "sendTask",
    "receive": "receiveTask",
    "manual": "manualTask",
    "task": "task",
}


@dataclass
class Node:
    id: str
    name: str
    kind: str                      # user/service/rule/send/manual/start/end/catch/boundary/xor/and
    lane: str
    col: int
    row: int = 0
    event_def: str | None = None   # message / timer / terminate
    attached_to: str | None = None # tylko dla boundary
    doc: str = ""
    # --- pola uzywane tylko w wariancie wykonywalnym (Camunda 8 / Zeebe) ---
    job_type: str | None = None      # zadanie uslugowe: typ zadania dla workera
    candidate_groups: str | None = None  # zadanie uzytkownika: grupa, ktora je widzi
    timer: str | None = None         # zdarzenie czasowe: ISO 8601, np. P14D
    message_name: str | None = None  # zdarzenie komunikatu
    decision_id: str | None = None   # zadanie regul: decyzja DMN wolana przez silnik
    result_variable: str | None = None   # zmienna z wynikiem decyzji
    outputs: list | None = None      # mapowanie wyjscia: [(zmienna, wyrazenie FEEL)]

    @property
    def shape(self) -> str:
        if self.kind in ("xor", "and"):
            return "gateway"
        if self.kind in ("start", "end", "catch", "boundary"):
            return "event"
        return "task"

    @property
    def size(self):
        return SIZES[self.shape]


@dataclass
class Flow:
    id: str
    src: str
    dst: str
    name: str = ""
    condition: str | None = None     # wyrazenie FEEL na przeplywie warunkowym
    default: bool = False            # przeplyw domyslny bramki


@dataclass
class Lane:
    id: str
    name: str
    rows: int = 1


@dataclass
class Pool:
    id: str
    name: str
    process_id: str | None = None   # None = pula czarna skrzynka
    lanes: list = field(default_factory=list)
    nodes: list = field(default_factory=list)
    flows: list = field(default_factory=list)
    height: int = 80                # uzywane tylko dla czarnej skrzynki


@dataclass
class Message:
    id: str
    src: str
    dst: str
    name: str = ""


class Diagram:
    def __init__(self, ident: str, name: str, cols: int):
        self.id = ident
        self.name = name
        self.cols = cols
        self.zeebe = False      # True = wariant wykonywalny dla Camunda 8
        self.pools: list[Pool] = []
        self.messages: list[Message] = []
        self._geo: dict[str, tuple[int, int, int, int]] = {}
        self._lane_geo: dict[str, tuple[int, int, int, int]] = {}
        self._pool_geo: dict[str, tuple[int, int, int, int]] = {}

    # ---------- budowa ----------
    def pool(self, *a, **kw) -> Pool:
        p = Pool(*a, **kw)
        self.pools.append(p)
        return p

    def msg(self, ident, src, dst, name=""):
        self.messages.append(Message(ident, src, dst, name))

    def node_of(self, ident: str) -> Node:
        for p in self.pools:
            for n in p.nodes:
                if n.id == ident:
                    return n
        raise KeyError("nieznany element: " + ident)

    # ---------- uklad ----------
    def layout(self):
        pool_w = LANE_LABEL_W + self.cols * COL_W + 60
        y = 80
        for pool in self.pools:
            if pool.process_id is None:
                self._pool_geo[pool.id] = (POOL_X, y, pool_w, pool.height)
                y += pool.height + POOL_GAP
                continue

            lane_y = y
            pool_h = 0
            for lane in pool.lanes:
                used = max([n.row for n in pool.nodes if n.lane == lane.id] + [0]) + 1
                lane.rows = max(lane.rows, used)
                lane_h = lane.rows * ROW_H + 2 * LANE_PAD
                self._lane_geo[lane.id] = (
                    POOL_X + LANE_LABEL_W, lane_y, pool_w - LANE_LABEL_W, lane_h
                )
                for n in [x for x in pool.nodes if x.lane == lane.id]:
                    w, h = n.size
                    cx = POOL_X + LANE_LABEL_W + 50 + n.col * COL_W + SIZES["task"][0] // 2
                    cy = lane_y + LANE_PAD + n.row * ROW_H + ROW_H // 2
                    self._geo[n.id] = (cx - w // 2, cy - h // 2, w, h)
                lane_y += lane_h
                pool_h += lane_h
            self._pool_geo[pool.id] = (POOL_X, y, pool_w, pool_h)
            y += pool_h + POOL_GAP

        # zdarzenia brzegowe siadaja na dolnej krawedzi zadania
        for pool in self.pools:
            for n in pool.nodes:
                if n.kind == "boundary" and n.attached_to:
                    ax, ay, aw, ah = self._geo[n.attached_to]
                    w, h = n.size
                    self._geo[n.id] = (ax + aw - 45, ay + ah - h // 2, w, h)

    def _bounds(self, ident):
        if ident in self._geo:
            return self._geo[ident]
        return self._pool_geo[ident]          # komunikat wpiety w cala pule

    def waypoints(self, src, dst):
        sx, sy, sw, sh = self._bounds(src)
        tx, ty, tw, th = self._bounds(dst)
        # komunikat do puli czarnej skrzynki wchodzi pionowo, pod elementem po drugiej stronie
        if src in self._pool_geo:
            sx, sw = tx, tw
        if dst in self._pool_geo:
            tx, tw = sx, sw
        scx, scy = sx + sw // 2, sy + sh // 2
        tcx, tcy = tx + tw // 2, ty + th // 2

        if tx > sx + sw - 5:                       # w prawo
            if abs(scy - tcy) < 6:
                return [(sx + sw, scy), (tx, tcy)]
            midx = (sx + sw + tx) // 2
            return [(sx + sw, scy), (midx, scy), (midx, tcy), (tx, tcy)]
        if tx + tw < sx + 5:                       # powrot w lewo - dolem
            below = max(sy + sh, ty + th) + 45
            return [(scx, sy + sh), (scx, below), (tcx, below), (tcx, ty + th)]
        if tcy > scy:                              # w dol
            return [(scx, sy + sh), (tcx, ty)]
        return [(scx, sy), (tcx, ty + th)]         # w gore

    # ---------- serializacja ----------
    def xml(self) -> str:
        e = html.escape
        L: list[str] = []
        L.append('<?xml version="1.0" encoding="UTF-8"?>')
        L.append(
            '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" '
            'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" '
            'xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
            'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            + ('xmlns:zeebe="http://camunda.org/schema/zeebe/1.0" ' if self.zeebe else '')
            + 'id="Definitions_' + self.id + '" '
            'targetNamespace="http://bpmn.io/schema/bpmn" '
            'exporter="gen_bpmn.py (Mateusz Biernat)" exporterVersion="1.0">'
        )
        L.append('  <bpmn:collaboration id="Collab_' + self.id + '">')
        for p in self.pools:
            ref = ' processRef="' + p.process_id + '"' if p.process_id else ""
            L.append('    <bpmn:participant id="' + p.id + '" name="' + e(p.name) + '"' + ref + ' />')
        for m in self.messages:
            L.append(
                '    <bpmn:messageFlow id="' + m.id + '" name="' + e(m.name) + '" '
                'sourceRef="' + m.src + '" targetRef="' + m.dst + '" />'
            )
        L.append('  </bpmn:collaboration>')
        if self.zeebe:
            for p in self.pools:
                for n in p.nodes:
                    if n.message_name:
                        L.append('  <bpmn:message id="Msg_' + n.id + '" name="'
                                 + e(n.message_name) + '" />')

        for p in self.pools:
            if not p.process_id:
                continue
            wykonywalny = "true" if self.zeebe else "false"
            L.append('  <bpmn:process id="' + p.process_id + '" isExecutable="' + wykonywalny + '">')
            if p.lanes:
                L.append('    <bpmn:laneSet id="LS_' + p.process_id + '">')
                for lane in p.lanes:
                    L.append('      <bpmn:lane id="' + lane.id + '" name="' + e(lane.name) + '">')
                    for n in [x for x in p.nodes if x.lane == lane.id]:
                        L.append('        <bpmn:flowNodeRef>' + n.id + '</bpmn:flowNodeRef>')
                    L.append('      </bpmn:lane>')
                L.append('    </bpmn:laneSet>')
            for n in p.nodes:
                L.extend("    " + s for s in self._node_xml(n, p))
            for f in p.flows:
                nm = ' name="' + e(f.name) + '"' if f.name else ""
                if self.zeebe and f.condition:
                    L.append('    <bpmn:sequenceFlow id="' + f.id + '"' + nm +
                             ' sourceRef="' + f.src + '" targetRef="' + f.dst + '">')
                    L.append('      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">'
                             + e(f.condition) + '</bpmn:conditionExpression>')
                    L.append('    </bpmn:sequenceFlow>')
                else:
                    L.append(
                        '    <bpmn:sequenceFlow id="' + f.id + '"' + nm +
                        ' sourceRef="' + f.src + '" targetRef="' + f.dst + '" />'
                    )
            L.append('  </bpmn:process>')

        L.append('  <bpmndi:BPMNDiagram id="Dia_' + self.id + '">')
        L.append('    <bpmndi:BPMNPlane id="Plane_' + self.id + '" bpmnElement="Collab_' + self.id + '">')
        for p in self.pools:
            x, y, w, h = self._pool_geo[p.id]
            L.append('      <bpmndi:BPMNShape id="S_' + p.id + '" bpmnElement="' + p.id + '" isHorizontal="true">')
            L.append('        <dc:Bounds x="%d" y="%d" width="%d" height="%d" />' % (x, y, w, h))
            L.append('      </bpmndi:BPMNShape>')
            for lane in p.lanes:
                lx, ly, lw, lh = self._lane_geo[lane.id]
                L.append('      <bpmndi:BPMNShape id="S_' + lane.id + '" bpmnElement="' + lane.id + '" isHorizontal="true">')
                L.append('        <dc:Bounds x="%d" y="%d" width="%d" height="%d" />' % (lx, ly, lw, lh))
                L.append('      </bpmndi:BPMNShape>')
            for n in p.nodes:
                x, y, w, h = self._geo[n.id]
                extra = ' isMarkerVisible="true"' if n.kind == "xor" else ""
                L.append('      <bpmndi:BPMNShape id="S_' + n.id + '" bpmnElement="' + n.id + '"' + extra + '>')
                L.append('        <dc:Bounds x="%d" y="%d" width="%d" height="%d" />' % (x, y, w, h))
                if n.shape == "event" and n.name:
                    L.append('        <bpmndi:BPMNLabel>')
                    L.append('          <dc:Bounds x="%d" y="%d" width="110" height="27" />' % (x - 37, y + h + 6))
                    L.append('        </bpmndi:BPMNLabel>')
                L.append('      </bpmndi:BPMNShape>')
        for p in self.pools:
            for f in p.flows:
                L.extend(self._edge_xml(f.id, f.src, f.dst))
        for m in self.messages:
            L.extend(self._edge_xml(m.id, m.src, m.dst))
        L.append('    </bpmndi:BPMNPlane>')
        L.append('  </bpmndi:BPMNDiagram>')
        L.append('</bpmn:definitions>')
        return "\n".join(L) + "\n"

    def _edge_xml(self, ident, src, dst):
        out = ['      <bpmndi:BPMNEdge id="E_' + ident + '" bpmnElement="' + ident + '">']
        for wx, wy in self.waypoints(src, dst):
            out.append('        <di:waypoint x="%d" y="%d" />' % (wx, wy))
        out.append('      </bpmndi:BPMNEdge>')
        return out

    def _node_xml(self, n: Node, pool: Pool):
        e = html.escape
        ins = [f.id for f in pool.flows if f.dst == n.id]
        outs = [f.id for f in pool.flows if f.src == n.id]
        body = []
        if n.doc:
            body.append('  <bpmn:documentation>' + e(n.doc) + '</bpmn:documentation>')
        # kolejnosc wg schemy BPMN: documentation, extensionElements, incoming, outgoing
        if self.zeebe:
            body += self._zeebe_ext(n)
        body += ['  <bpmn:incoming>' + i + '</bpmn:incoming>' for i in ins]
        body += ['  <bpmn:outgoing>' + o + '</bpmn:outgoing>' for o in outs]

        if n.kind == "start":
            tag, attrs = "startEvent", ""
        elif n.kind == "end":
            tag, attrs = "endEvent", ""
        elif n.kind == "catch":
            tag, attrs = "intermediateCatchEvent", ""
        elif n.kind == "boundary":
            tag, attrs = "boundaryEvent", ' attachedToRef="' + (n.attached_to or "") + '" cancelActivity="true"'
        elif n.kind == "xor":
            tag, attrs = "exclusiveGateway", ""
        elif n.kind == "and":
            tag, attrs = "parallelGateway", ""
        else:
            tag, attrs = TASK_TYPES[n.kind], ""

        if n.kind == "xor" and self.zeebe:
            domyslny = [f.id for f in pool.flows if f.src == n.id and f.default]
            if domyslny:
                attrs += ' default="' + domyslny[0] + '"'

        if n.event_def == "message":
            ref = ' messageRef="Msg_' + n.id + '"' if (self.zeebe and n.message_name) else ''
            body.append('  <bpmn:messageEventDefinition id="MED_' + n.id + '"' + ref + ' />')
        elif n.event_def == "timer":
            if self.zeebe and n.timer:
                body.append('  <bpmn:timerEventDefinition id="TED_' + n.id + '">')
                body.append('    <bpmn:timeDuration xsi:type="bpmn:tFormalExpression">'
                            + e(n.timer) + '</bpmn:timeDuration>')
                body.append('  </bpmn:timerEventDefinition>')
            else:
                body.append('  <bpmn:timerEventDefinition id="TED_' + n.id + '" />')
        elif n.event_def == "terminate":
            body.append('  <bpmn:terminateEventDefinition id="TRD_' + n.id + '" />')

        head = '<bpmn:' + tag + ' id="' + n.id + '" name="' + e(n.name) + '"' + attrs + '>'
        return [head] + body + ['</bpmn:' + tag + '>']


    def _zeebe_ext(self, n: Node):
        """Rozszerzenia Camunda 8: typ zadania dla workera, zadanie uzytkownika, grupa."""
        e = html.escape
        wnetrze = []
        if n.decision_id:
            wnetrze.append('    <zeebe:calledDecision decisionId="' + e(n.decision_id)
                           + '" resultVariable="' + e(n.result_variable or "wynik") + '" />')
        if n.outputs:
            wnetrze.append('    <zeebe:ioMapping>')
            for zmienna, wyrazenie in n.outputs:
                wnetrze.append('      <zeebe:output source="' + e(wyrazenie)
                               + '" target="' + e(zmienna) + '" />')
            wnetrze.append('    </zeebe:ioMapping>')
        if n.job_type:
            wnetrze.append('    <zeebe:taskDefinition type="' + e(n.job_type) + '" retries="3" />')
        if n.kind == "user":
            wnetrze.append('    <zeebe:userTask />')
            if n.candidate_groups:
                wnetrze.append('    <zeebe:assignmentDefinition candidateGroups="'
                               + e(n.candidate_groups) + '" />')
        if not wnetrze:
            return []
        return ['  <bpmn:extensionElements>'] + wnetrze + ['  </bpmn:extensionElements>']


def sanity(d: Diagram) -> list[str]:
    """Sprawdza spojnosc modelu przed zapisem - zly plik nie otworzy sie w modelerze."""
    problems = []
    ids = set()
    for p in d.pools:
        ids.add(p.id)
        for lane in p.lanes:
            ids.add(lane.id)
        for n in p.nodes:
            if n.id in ids:
                problems.append("zdublowany id: " + n.id)
            ids.add(n.id)
    for p in d.pools:
        for f in p.flows:
            if f.id in ids:
                problems.append("zdublowany id przeplywu: " + f.id)
            ids.add(f.id)
            for ref in (f.src, f.dst):
                if ref not in ids:
                    problems.append("przeplyw " + f.id + " wskazuje na nieznany element " + ref)
    for m in d.messages:
        for ref in (m.src, m.dst):
            if ref not in ids:
                problems.append("komunikat " + m.id + " wskazuje na nieznany element " + ref)
    for p in d.pools:
        for n in p.nodes:
            if n.kind == "boundary":
                if n.attached_to not in ids:
                    problems.append(n.id + " wisi na nieznanym zadaniu")
                continue
            has_in = any(f.dst == n.id for f in p.flows)
            has_out = any(f.src == n.id for f in p.flows)
            if n.kind != "start" and not has_in:
                problems.append(n.id + " nie ma wejscia")
            if n.kind != "end" and not has_out:
                problems.append(n.id + " nie ma wyjscia")
    return problems
