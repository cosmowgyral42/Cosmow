/**
 * @typedef {{
 *   id: number,
 *   title: string,
 *   original_filename: string,
 *   content_type: string,
 *   file_size_bytes: number,
 *   status: string
 * }} DocumentResponse
 */

/**
 * @typedef {{
 *   document_id: number,
 *   chunks_embedded: number,
 *   status: string
 * }} EmbeddingResponse
 */

/**
 * @typedef {{
 *   document_id: number,
 *   chunk_id: number,
 *   title: string,
 *   similarity: number
 * }} RAGSource
 */

/**
 * @typedef {{
 *   answer: string,
 *   sources: RAGSource[]
 * }} RAGAnswer
 */
export {};
