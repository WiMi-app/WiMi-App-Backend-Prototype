from typing import Any, Dict, List, Optional
from supabase import Client
from fastapi import HTTPException, status

def get_from_supabase(
    db: Client,
    table_name: str,
    match: Optional[Dict[str, Any]] = None,
    single: bool = False,
    order_by: Optional[str] = None,
    desc: bool = False,
    range_from: Optional[int] = None,
    range_to: Optional[int] = None,
) -> List[Dict[str, Any]]:
    query = db.table(table_name).select("*")

    if match:
        for key, value in match.items():
            query = query.eq(key, value)

    if order_by:
        query = query.order(order_by, desc=desc)

    if range_from is not None and range_to is not None:
        query = query.range(range_from, range_to)

    result = query.execute()

    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No matching records found in {table_name}",
        )

    if single:
        return result.data[0]

    return result.data

def insert_into_supabase(db: Client, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    result = db.table(table_name).insert(data).execute()
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to insert data into {table_name}",
        )
    return result.data[0]


def update_supabase(db: Client, table_name: str, update_data: Dict[str, Any], match: Dict[str, Any]) -> Dict[str, Any]:
    result = db.table(table_name).update(update_data).match(match).execute()
    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update data in {table_name}",
        )
    return result.data[0]

def delete_from_supabase(
    db: Client,
    table_name: str,
    match: Dict[str, Any],
) -> None:
    result = db.table(table_name).delete().match(match).execute()
    if result.status_code >= 400 or not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete from {table_name} where {match}",
        )
