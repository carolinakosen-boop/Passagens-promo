#!/usr/bin/env python3
"""Extract and clean data from the Google Sheets XLSX into a JSON file for the dashboard."""
import pandas as pd
import json
import warnings
import math

warnings.filterwarnings("ignore")

XLSX_PATH = "spreadsheet.xlsx"
OUTPUT_PATH = "docs/data.json"


def safe(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    return val


def extract_visao_geral(xlsx):
    df = pd.read_excel(xlsx, sheet_name="Visão Geral da Carteira", header=None)
    summary = df.iloc[0].tolist()
    data = df.iloc[2:].copy()
    data.columns = [
        "idx", "corretor", "id_cliente", "data_primeiro_contrato",
        "dias_sem_contrato", "status", "carteira", "contratos_ate_30_04",
        "contrato_ativo_maio", "lost",
    ]
    data = data.dropna(subset=["corretor"])

    clients = []
    for _, row in data.iterrows():
        clients.append({
            "corretor": safe(row["corretor"]),
            "dias_sem_contrato": int(row["dias_sem_contrato"]) if pd.notna(row["dias_sem_contrato"]) else None,
            "status": safe(row["status"]),
            "carteira": safe(row["carteira"]),
            "contratos_ate_30_04": int(row["contratos_ate_30_04"]) if pd.notna(row["contratos_ate_30_04"]) else 0,
            "contrato_ativo_maio": int(row["contrato_ativo_maio"]) if pd.notna(row["contrato_ativo_maio"]) else 0,
            "lost": safe(row["lost"]),
        })

    status_counts = {}
    carteira_counts = {}
    lost_counts = {}
    for c in clients:
        s = c["status"] or "Desconhecido"
        status_counts[s] = status_counts.get(s, 0) + 1
        ca = c["carteira"] or "Desconhecido"
        carteira_counts[ca] = carteira_counts.get(ca, 0) + 1
        lo = c["lost"] or "N/A"
        lost_counts[lo] = lost_counts.get(lo, 0) + 1

    total_contratos_maio = sum(c["contrato_ativo_maio"] for c in clients)
    total_contratos_anterior = sum(c["contratos_ate_30_04"] for c in clients)

    return {
        "total_clientes": int(safe(summary[2]) or len(clients)),
        "media_contratos": round(float(safe(summary[7]) or 0), 2),
        "contratos_emitidos_ate_abril": int(safe(summary[8]) or total_contratos_anterior),
        "contratos_ativos_maio": int(safe(summary[9]) or total_contratos_maio),
        "status_distribution": status_counts,
        "carteira_distribution": carteira_counts,
        "lost_distribution": lost_counts,
        "clients": clients,
    }


def extract_meta_geral(xlsx):
    df = pd.read_excel(xlsx, sheet_name="Meta Geral 052025", header=None)
    rows = []
    for i in range(len(df)):
        rows.append([safe(v) for v in df.iloc[i].tolist()])

    return {
        "contratos": {
            "meta": int(float(rows[5][1])) if rows[5][1] else 0,
            "realizado": int(float(rows[5][3])) if rows[5][3] else 0,
            "percentual": round(float(rows[5][5]) * 100, 1) if rows[5][5] else 0,
        },
        "retencao": {
            "clientes_totais": int(float(rows[5][7])) if rows[5][7] else 0,
            "percentual_retencao": round(float(rows[5][9]) * 100, 1) if rows[5][9] else 0,
            "clientes_para_reverter": round(float(rows[5][11]), 1) if rows[5][11] else 0,
        },
        "onboarding": {
            "meta": int(float(rows[9][1])) if rows[9][1] else 0,
            "realizado": int(float(rows[9][3])) if rows[9][3] else 0,
            "percentual": round(float(rows[9][5]) * 100, 1) if rows[9][5] else 0,
            "clientes_revertidos": int(float(rows[9][7])) if rows[9][7] else 0,
        },
        "ongoing": {
            "meta": int(float(rows[13][1])) if rows[13][1] else 0,
            "realizado": int(float(rows[13][3])) if rows[13][3] else 0,
            "percentual": round(float(rows[13][5]) * 100, 1) if rows[13][5] else 0,
        },
    }


def extract_meta_individual(xlsx):
    df = pd.read_excel(xlsx, sheet_name="Meta Individual", header=None)
    rows = []
    for i in range(len(df)):
        rows.append([safe(v) for v in df.iloc[i].tolist()])

    specialists = []

    # Camila (rows 2-5, Onboarding)
    specialists.append({
        "nome": "Camila",
        "tipo": "Onboarding",
        "clientes": int(float(rows[5][4])) if rows[5][4] else 0,
        "meta_contratos": int(float(rows[5][5])) if rows[5][5] else 0,
        "contratos_ativos": int(float(rows[5][6])) if rows[5][6] else 0,
        "percentual_contratos": round(float(rows[5][7]) * 100, 1) if rows[5][7] else 0,
        "segundo_contrato": int(float(rows[5][11])) if rows[5][11] else 0,
        "resultado_final": round(float(rows[3][14]) * 100, 1) if rows[3][14] else 0,
    })

    # Andressa (rows 9-12, Ongoing)
    specialists.append({
        "nome": "Andressa",
        "tipo": "Ongoing",
        "clientes": int(float(rows[12][4])) if rows[12][4] else 0,
        "meta_contratos": int(float(rows[12][5])) if rows[12][5] else 0,
        "contratos_ativos": int(float(rows[12][6])) if rows[12][6] else 0,
        "percentual_contratos": round(float(rows[12][7]) * 100, 1) if rows[12][7] else 0,
        "clientes_risco": int(float(rows[12][9])) if rows[12][9] else 0,
        "meta_reversao": round(float(rows[12][10]), 1) if rows[12][10] else 0,
        "clientes_revertidos": int(float(rows[12][11])) if rows[12][11] else 0,
        "resultado_final": round(float(rows[10][14]) * 100, 1) if rows[10][14] else 0,
    })

    # Emanuelle (rows 16-19, Ongoing)
    specialists.append({
        "nome": "Emanuelle",
        "tipo": "Ongoing",
        "clientes": int(float(rows[19][4])) if rows[19][4] else 0,
        "meta_contratos": int(float(rows[19][5])) if rows[19][5] else 0,
        "contratos_ativos": int(float(rows[19][6])) if rows[19][6] else 0,
        "percentual_contratos": round(float(rows[19][7]) * 100, 1) if rows[19][7] else 0,
        "clientes_risco": int(float(rows[19][9])) if rows[19][9] else 0,
        "meta_reversao": round(float(rows[19][10]), 1) if rows[19][10] else 0,
        "clientes_revertidos": int(float(rows[19][11])) if rows[19][11] else 0,
        "resultado_final": round(float(rows[17][14]) * 100, 1) if rows[17][14] else 0,
    })

    return specialists


def extract_churn(xlsx):
    df = pd.read_excel(xlsx, sheet_name="Visão Churn", header=None)
    rows = []
    for i in range(len(df)):
        rows.append([safe(v) for v in df.iloc[i].tolist()])

    churn_ranges = []
    for i in range(2, 13):
        r = rows[i]
        label = r[3]
        tempo = r[4]
        count = r[5]
        if label and count:
            churn_ranges.append({
                "range": str(label),
                "tempo": str(tempo) if tempo else "",
                "count": int(float(count)),
            })
    return churn_ranges


def extract_contratos_vencidos(xlsx):
    df = pd.read_excel(xlsx, sheet_name="Contratos vencidos e a pagar", header=None)
    rows = []
    for i in range(1, len(df)):
        r = df.iloc[i].tolist()
        rows.append({
            "especialista": safe(r[0]),
            "status": safe(r[1]),
            "nome": safe(r[3]),
            "data_criacao": str(r[4])[:10] if pd.notna(r[4]) else None,
            "data_termino": str(r[7])[:10] if pd.notna(r[7]) else None,
        })
    
    status_counts = {}
    esp_counts = {}
    for c in rows:
        s = c["status"] or "Desconhecido"
        status_counts[s] = status_counts.get(s, 0) + 1
        e = c["especialista"] or "Desconhecido"
        esp_counts[e] = esp_counts.get(e, 0) + 1

    return {
        "total": len(rows),
        "status_counts": status_counts,
        "por_especialista": esp_counts,
        "items": rows[:30],
    }


def extract_lost_clients(xlsx):
    df = pd.read_excel(xlsx, sheet_name="Clientes em Lost", header=None)
    clients = []
    for i in range(2, len(df)):
        r = df.iloc[i].tolist()
        clients.append({
            "corretor": safe(r[0]),
            "dias_sem_contrato": int(float(r[3])) if pd.notna(r[3]) else None,
            "contratos_anteriores": int(float(r[5])) if pd.notna(r[5]) else 0,
            "motivo": safe(r[6]),
            "consideracoes": safe(r[7]),
        })

    motivo_counts = {}
    for c in clients:
        m = c["motivo"] or "Nenhum"
        motivo_counts[m] = motivo_counts.get(m, 0) + 1

    return {
        "total": len(clients),
        "motivo_counts": motivo_counts,
        "items": clients,
    }


def main():
    xlsx = pd.ExcelFile(XLSX_PATH)

    visao = extract_visao_geral(xlsx)
    meta = extract_meta_geral(xlsx)
    individual = extract_meta_individual(xlsx)
    churn = extract_churn(xlsx)
    contratos = extract_contratos_vencidos(xlsx)
    lost = extract_lost_clients(xlsx)

    dashboard_data = {
        "titulo": "[Maio] Carteira CS",
        "periodo": "Maio 2025",
        "visao_geral": visao,
        "meta_geral": meta,
        "meta_individual": individual,
        "churn": churn,
        "contratos_vencidos": contratos,
        "clientes_lost": lost,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)

    print(f"Data extracted to {OUTPUT_PATH}")
    print(f"  Total clients: {visao['total_clientes']}")
    print(f"  Contratos meta: {meta['contratos']['meta']} | Realizado: {meta['contratos']['realizado']}")
    print(f"  Lost clients: {lost['total']}")
    print(f"  Churn ranges: {len(churn)}")


if __name__ == "__main__":
    main()
