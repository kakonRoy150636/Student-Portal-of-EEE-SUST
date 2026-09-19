from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lab import EquipmentAsset, EquipmentModel


class LabService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_equipment(self):
        """List every equipment asset joined with its model/category."""
        stmt = (
            select(EquipmentModel.model_name, EquipmentModel.category, EquipmentAsset.asset_tag, EquipmentAsset.lab_name, EquipmentAsset.condition)
            .join(EquipmentAsset, EquipmentAsset.model_id == EquipmentModel.id)
            .order_by(EquipmentModel.category, EquipmentAsset.asset_tag)
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "tag": tag,
                "model": model,
                "category": category,
                "lab": lab_name,
                "status": condition,
            }
            for model, category, tag, lab_name, condition in rows
        ]