"""
Parser YAML simples para evitar dependências externas
Suporta apenas as estruturas necessárias para o simulador
"""

import re

class SimpleYAMLParser:
    def __init__(self):
        self.data = {}
    
    def load(self, file_path):
        """Carrega e parseia um arquivo YAML simples"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self._parse(content)
    
    def _parse(self, content):
        """Parseia o conteúdo YAML"""
        lines = content.split('\n')
        result = {}
        current_section = result
        section_stack = [result]
        indent_stack = [0]
        
        for line in lines:
            line = line.rstrip()
            if not line or line.strip().startswith('#'):
                continue
            
            indent = len(line) - len(line.lstrip())
            line = line.strip()
            
            while len(indent_stack) > 1 and indent <= indent_stack[-1]:
                indent_stack.pop()
                section_stack.pop()
            
            current_section = section_stack[-1]
            
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if not value:
                    new_section = {}
                    current_section[key] = new_section
                    section_stack.append(new_section)
                    indent_stack.append(indent)
                else:
                    current_section[key] = self._parse_value(value)
        
        return result
    
    def _parse_value(self, value):
        """Converte string para tipo apropriado"""
        value = value.strip()
        
        if value.lower() in ('true', 'yes', 'on'):
            return True
        elif value.lower() in ('false', 'no', 'off'):
            return False
        
        elif value.lower() in ('null', 'none', '~', ''):
            return None
        
        elif value == '.inf':
            return float('inf')
        
        elif self._is_number(value):
            if '.' in value:
                return float(value)
            else:
                return int(value)
        
        else:
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                return value[1:-1]
            return value
    
    def _is_number(self, value):
        """Verifica se uma string representa um número"""
        try:
            float(value)
            return True
        except ValueError:
            return False
