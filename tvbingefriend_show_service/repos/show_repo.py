"""Repository for shows"""
import logging
from typing import Any

from sqlalchemy import inspect, Select
from sqlalchemy.dialects.mysql import Insert, insert as mysql_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, Mapper, ColumnProperty

from tvbingefriend_show_service.models.show import Show


# noinspection PyMethodMayBeStatic
class ShowRepository:
    """Repository for shows"""
    def upsert_show(self, show: dict[str, Any], db: Session) -> None:
        """Upsert a show in the database

        Args:
            show (dict[str, Any]): Show to upsert
            db (Session): Database session
        """
        show_id: int | None = show.get("id")  # get show_id from show
        logging.debug(f"ShowRepository.upsert_show: show_id: {show_id}")

        if not show_id:  # if show_id is missing, log error and return
            logging.error("show_repository.upsert_show: Error upserting show: Show must have a show_id")
            return

        mapper: Mapper = inspect(Show)  # get show mapper
        show_columns: set[str] = {  # get show columns
            prop.key for prop in mapper.attrs.values() if isinstance(prop, ColumnProperty)
        }

        insert_values: dict[str, Any] = {  # create insert values
            key: value for key, value in show.items() if key in show_columns
        }
        insert_values["id"] = show_id  # add id value to insert values

        update_values: dict[str, Any] = {  # create update values
            key: value for key, value in insert_values.items() if key != "id"
        }

        try:

            # noinspection PyTypeHints
            stmt: Insert = mysql_insert(Show).values(insert_values)  # create insert statement
            stmt = stmt.on_duplicate_key_update(**update_values)  # add duplicate key update statement

            db.execute(stmt)  # execute insert statement
            db.flush()  # flush changes

        except SQLAlchemyError as e:  # catch any SQLAchemy errors and log them
            logging.error(f"show_repository.upsert_show: Database error during upsert of show_id {show_id}: {e}")
        except Exception as e:  # catch any other errors and log them
            logging.error(f"show_repository.upsert_show: Unexpected error during upsert of show show_id {show_id}: {e}")

    def get_show_by_id(self, show_id: int, db: Session) -> Show | None:
        """Get a show by its ID

        Args:
            show_id (int): Show ID
            db (Session): Database session

        Returns:
            Show | None: Show object or None if not found
        """
        try:
            show = db.query(Show).filter(Show.id == show_id).first()
            return show
        except SQLAlchemyError as e:
            logging.error(f"show_repository.get_show_by_id: Database error getting show_id {show_id}: {e}")
            return None
        except Exception as e:
            logging.error(f"show_repository.get_show_by_id: Unexpected error getting show_id {show_id}: {e}")
            return None

    def search_shows(self, query: str, limit: int = 20, offset: int = 0, db: Session | None = None) -> list[Show]:
        """Search shows by name with optimized query

        Args:
            query (str): Search query string
            limit (int): Maximum number of results to return (default 20)
            offset (int): Number of results to skip for pagination (default 0)
            db (Session): Database session

        Returns:
            list[Show]: List of matching shows ordered by relevance
        """
        try:
            if not query or not query.strip() or db is None:
                return []

            query = query.strip()

            # Optimized search query with multiple strategies for instant results
            search_query = db.query(Show)

            # Strategy 1: Exact name match (highest priority)
            exact_matches = search_query.filter(Show.name.ilike(query)).limit(5).all()

            # Strategy 2: Starts with query (second priority)
            prefix_matches = search_query.filter(
                Show.name.ilike(f"{query}%")
            ).filter(
                ~Show.name.ilike(query)  # Exclude exact matches already found
            ).limit(10).all()

            # Strategy 3: Contains query anywhere (third priority)
            contains_matches = search_query.filter(
                Show.name.ilike(f"%{query}%")
            ).filter(
                ~Show.name.ilike(query),  # Exclude exact matches
                ~Show.name.ilike(f"{query}%")  # Exclude prefix matches
            ).order_by(
                Show.weight.desc()  # Order by popularity/weight (MySQL compatible)
            ).limit(limit - len(exact_matches) - len(prefix_matches)).all()

            # Combine results in order of relevance
            results = exact_matches + prefix_matches + contains_matches

            # Apply offset and limit to final results
            return results[offset:offset + limit] if offset > 0 else results[:limit]

        except SQLAlchemyError as e:
            logging.error(f"show_repository.search_shows: Database error searching for '{query}': {e}")
            return []
        except Exception as e:
            logging.error(f"show_repository.search_shows: Unexpected error searching for '{query}': {e}")
            return []

    def get_shows_bulk(self, db: Session, offset: int | None = 0, limit: int | None = 100) -> list[Show]:
        """Get shows bulk

        Args:
            offset (int): Offset for pagination (default 0)
            limit (int): Maximum number of results to return (default 100)
            db (Session): Database session

        Returns:
            list[Show]: List of matching shows ordered by relevance
        """
        try:
            stmt: Select = Select(Show).order_by(Show.id).offset(offset).limit(limit)
            shows_bulk: list[Show] | None = list(db.execute(stmt).scalars().all())

            if not shows_bulk:
                return []

            return shows_bulk

        except SQLAlchemyError as e:
            logging.error(f"ShowRepository.get_shows_bulk: Database error getting shows bulk: {e}")
            return []
        except Exception as e:
            logging.error(f"ShowRepository.get_shows_bulk: Unexpected error getting show bulk: {e}")
            return []
