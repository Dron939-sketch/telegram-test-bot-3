# loop_analyzer.py
from typing import List, Dict, Optional, Any
from confinement_model import ConfinementModel9


class LoopAnalyzer:
    """
    Анализирует рекурсивные петли в конфайнмент-модели
    """
    
    def __init__(self, model: ConfinementModel9):
        self.model = model
        self.significant_loops = []
        self._visited = set()
        self._path = []
    
    def analyze(self) -> List[Dict[str, Any]]:
        """
        Главный метод анализа - возвращает все значимые петли
        """
        self.significant_loops = []
        self._find_all_cycles()
        self._rank_loops_by_impact()
        self._describe_loops()
        
        return self.significant_loops
    
    def _find_all_cycles(self):
        """Находит все циклы в графе"""
        # Начинаем с каждого элемента
        for start_id in range(1, 10):
            self._visited.clear()
            self._path.clear()
            self._dfs(start_id, 0)
    
    def _dfs(self, node_id: int, depth: int):
        """Поиск в глубину для нахождения циклов"""
        if node_id in self._path:
            # Нашли цикл
            cycle_start = self._path.index(node_id)
            cycle = self._path[cycle_start:] + [node_id]
            if len(cycle) >= 3:  # минимум 3 элемента
                # Проверяем, что цикл уникальный
                cycle_set = set(cycle)
                is_unique = True
                for existing in self.significant_loops:
                    if set(existing['cycle']) == cycle_set:
                        is_unique = False
                        break
                
                if is_unique:
                    self.significant_loops.append({
                        'cycle': cycle.copy(),
                        'length': len(cycle),
                        'raw_strength': self._calculate_raw_strength(cycle)
                    })
            return
        
        if node_id in self._visited or node_id not in self.model.elements:
            return
        
        if not self.model.elements.get(node_id):
            return
        
        self._visited.add(node_id)
        self._path.append(node_id)
        
        element = self.model.elements[node_id]
        if element and element.causes:
            for next_id in element.causes:
                if next_id in self.model.elements:  # проверяем, что элемент существует
                    self._dfs(next_id, depth + 1)
        
        self._path.pop()
    
    def _calculate_raw_strength(self, cycle: List[int]) -> float:
        """Вычисляет сырую силу цикла"""
        strength = 1.0
        
        for i in range(len(cycle)-1):
            from_id = cycle[i]
            to_id = cycle[i+1]
            
            # Ищем связь
            found = False
            for link in self.model.links:
                if link['from'] == from_id and link['to'] == to_id:
                    strength *= link.get('strength', 0.5)
                    found = True
                    break
            
            if not found:
                # Если связи нет, используем слабую связь по умолчанию
                strength *= 0.3
        
        return min(strength, 1.0)
    
    def _rank_loops_by_impact(self):
        """Ранжирует петли по силе и длине"""
        for loop in self.significant_loops:
            # Чем длиннее петля, тем она значимее (охватывает больше системы)
            # Но при этом слабее (много слабых связей)
            length_factor = loop['length'] / 9.0  # нормализуем
            strength = loop['raw_strength']
            
            # Итоговая значимость
            loop['impact'] = length_factor * strength
    
    def _describe_loops(self):
        """Добавляет человеко-читаемые описания петель"""
        for loop in self.significant_loops:
            elements = loop['cycle']
            
            # Определяем тип петли по составу элементов
            has_result = 1 in elements
            has_closing = 9 in elements
            has_identity = 5 in elements or 6 in elements
            has_behavior = any(e in elements for e in [2, 3, 4])
            
            if has_result and has_closing and has_behavior:
                loop['type'] = 'master_loop'
                loop['description'] = '🔴 Главная петля, замыкающая всю систему'
                loop['color'] = 'red'
            elif has_identity and has_result:
                loop['type'] = 'identity_loop'
                loop['description'] = '🟠 Идентичность и симптомы усиливают друг друга'
                loop['color'] = 'orange'
            elif all(e in elements for e in [2, 3, 4]) or all(e in elements for e in [2, 4]):
                loop['type'] = 'behavioral_loop'
                loop['description'] = '🟡 Поведенческая петля: реакции зациклены'
                loop['color'] = 'yellow'
            elif has_closing:
                loop['type'] = 'closing_loop'
                loop['description'] = '🔵 Петля через замыкающий элемент'
                loop['color'] = 'blue'
            else:
                loop['type'] = 'minor_loop'
                loop['description'] = '⚪ Второстепенная петля'
                loop['color'] = 'gray'
    
    def get_strongest_loop(self) -> Optional[Dict[str, Any]]:
        """Возвращает самую сильную петлю"""
        if not self.significant_loops:
            return None
        
        return max(self.significant_loops, key=lambda x: x.get('impact', 0))
    
    def get_loops_by_type(self, loop_type: str) -> List[Dict[str, Any]]:
        """Возвращает петли определенного типа"""
        return [l for l in self.significant_loops if l.get('type') == loop_type]
    
    def get_intervention_points(self, loop: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Определяет точки разрыва петли"""
        elements = loop['cycle']
        
        # Точки разрыва - элементы с наибольшим влиянием
        intervention_points = []
        
        for elem_id in elements:
            elem = self.model.elements.get(elem_id)
            if not elem:
                continue
            
            # Оцениваем, насколько легко изменить этот элемент
            changeability = 1.0
            
            # Убеждения менять сложнее всего
            if elem.element_type in [self.model.TYPE_COMMON_CAUSE, 
                                     self.model.TYPE_CLOSING,
                                     self.model.TYPE_UPPER_CAUSE]:
                changeability = 0.3
            # Поведение менять проще
            elif elem.element_type == self.model.TYPE_IMMEDIATE_CAUSE:
                changeability = 0.7
            # Симптомы можно облегчить
            elif elem.element_type == self.model.TYPE_RESULT:
                changeability = 0.5
            
            intervention_points.append({
                'element_id': elem_id,
                'element': elem,
                'impact': elem.strength * changeability,
                'difficulty': 1 - changeability,
                'changeability': changeability,
                'name': elem.name,
                'type': elem.element_type
            })
        
        return sorted(intervention_points, key=lambda x: x['impact'], reverse=True)
    
    def get_break_points_summary(self) -> str:
        """Возвращает краткое резюме по точкам разрыва"""
        strongest = self.get_strongest_loop()
        if not strongest:
            return "Петли не обнаружены"
        
        points = self.get_intervention_points(strongest)
        if not points:
            return "Нет точек вмешательства"
        
        best = points[0]
        elem = best['element']
        
        return (f"🎯 Лучшая точка вмешательства: {elem.name}\n"
                f"   Сложность: {best['difficulty']:.0%}\n"
                f"   Потенциал: {best['impact']:.0%}")
