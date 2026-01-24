    def add_entry(self, entry):
        """Inserts an entry into the DB."""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO items (id, title, category, file_name, size_bytes, size_human,
                                       release_url, created_at, tags, is_encrypted, image, assets, priority)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry['id'],
                    entry['title'],
                    entry['category'],
                    entry['file_name'],
                    entry['size_bytes'],
                    entry['size_human'],
                    entry['release_url'],
                    entry['created_at'],
                    json.dumps(entry['tags']),
                    1 if entry['is_encrypted'] else 0,
                    entry['image'],
                    json.dumps(entry['assets']),
                    entry.get('priority', 1)
                ))
                conn.commit()

            self.trigger_sync(f"Added item: {entry['title']}")
            return True
        except Exception as e:
            logger.error(f"Add Entry Error: {e}")
            return False

    def get_all_tags(self):
        """Returns a list of all unique tags used in the library."""
        try:
            with self._get_conn() as conn:
                rows = conn.execute("SELECT tags FROM items").fetchall()

            all_tags = set()
            for row in rows:
                if row['tags']:
                    try:
                        tag_list = json.loads(row['tags'])
                        for t in tag_list:
                            if t.strip(): all_tags.add(t.strip())
                    except: pass

            return sorted(list(all_tags))
        except Exception as e:
            logger.error(f"Get Tags Error: {e}")
            return []

    def delete_entry(self, item_id):
        try:
            with self._get_conn() as conn:
                # 1. Get image to delete first
                row = conn.execute("SELECT image FROM items WHERE id = ?", (item_id,)).fetchone()
                image_to_delete = row['image'] if row else None

                # 2. Delete DB Row
                cursor = conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
                conn.commit()

                if cursor.rowcount > 0:
                    # 3. Delete image if row deleted successfully
                    if image_to_delete:
                        self._delete_image_file(image_to_delete)

                    self.trigger_sync(f"Deleted item {item_id}")
                    return True
        except Exception as e:
            logger.error(f"Delete Error: {e}")
        return False
